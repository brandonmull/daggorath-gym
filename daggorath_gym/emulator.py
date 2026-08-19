"""MAME operator — lifecycle management and hybrid IPC communication.

Encapsulates the MAME subprocess and two-channel IPC behind
a simple start/stop/recv/send API.

    State channel:   named pipe (FIFO) — MAME writes, Python reads
    Command channel: TCP socket         — Python writes, MAME reads

The state channel carries fixed-size tagged records (no delimiter):

    S  + 21-byte frame                                 state only changed
    T  + 1-byte comColor + 1024 pixel bytes            text only changed
    B  + 21-byte frame + 1-byte comColor + 1024 px     both changed
    M  + 1024-byte maze                                maze changed
    C  + 128-byte creature array                       creatures changed
    O  + 70-byte object record                         objects changed
"""

import os
import select
import socket
import subprocess
import time
from dataclasses import dataclass
from typing import Optional

from . import commands
from .paths import PROJECT_PATH, ROM_PATH, HASH_PATH, PLUGINS_PATH
from .screen import PIXEL_BYTES, decode_command_area
from .state import (
    CREATURE_BYTES,
    FRAME_LEN,
    MAZE_BYTES,
    OBJECTS_BYTES,
    DaggorathState,
)


# Record sizes keyed by the one-byte tag (fixed-size framing, binary-safe).
_RECORD_LENGTHS = {
    b"S": 1 + FRAME_LEN,
    b"T": 1 + 1 + PIXEL_BYTES,
    b"B": 1 + FRAME_LEN + 1 + PIXEL_BYTES,
    b"M": 1 + MAZE_BYTES,
    b"C": 1 + CREATURE_BYTES,
    b"O": 1 + OBJECTS_BYTES,
}

# Seconds to wait for the next state record before giving up.
_STATE_READ_TIMEOUT = 30.0


# ---------- Configuration ----------

@dataclass(frozen=True)
class IpcConfig:
    """Parameters for the hybrid IPC channels between Python and MAME."""
    state_fifo_path: str = "/tmp/daggorath-state"
    command_host: str = "127.0.0.1"
    command_port: int = 15001
    connection_timeout: float = 30


@dataclass(frozen=True)
class MameConfig:
    """Parameters for the MAME subprocess."""
    plugin_name: str = "daggorath"
    sound: str = "sdl"
    window: bool = True


# ---------- MameOperator ----------

class MameOperator:
    """Operates a MAME subprocess and communicates with it over hybrid IPC."""

    def __init__(
        self,
        mame_config: Optional[MameConfig] = None,
        ipc_config: Optional[IpcConfig] = None,
    ) -> None:
        self._mame_config = mame_config or MameConfig()
        self._ipc_config = ipc_config or IpcConfig()

        # ---------- the emulator itself ----------
        self._mame_process: Optional[subprocess.Popen] = None

        # ---------- state channel (FIFO) ----------
        self._state_fd: Optional[int] = None

        # ---------- command channel (TCP) ----------
        self._command_socket: Optional[socket.socket] = None
        self._command_connection: Optional[socket.socket] = None

        # ---------- receive buffer + reconstruction ----------
        self._receive_buffer = b""
        self._last_frame: Optional[bytes] = None
        self._last_command_text = ""
        self._last_maze: Optional[bytes] = None
        self._last_creatures: Optional[bytes] = None
        self._last_objects: Optional[bytes] = None

    # ---------- lifecycle ----------

    def start(self) -> None:
        """Create the state FIFO, open the command socket, launch MAME, and handshake."""

        # ---------- create the state FIFO ----------
        fifo_path = self._ipc_config.state_fifo_path
        self._remove_stale_fifo()
        os.mkfifo(fifo_path)
        self._state_fd = os.open(fifo_path, os.O_RDONLY | os.O_NONBLOCK)
        print(f"[MameOperator] State FIFO ready: {fifo_path}")

        # ---------- open the command socket ----------
        self._command_socket = self._create_listening_socket(self._ipc_config.command_port)

        # ---------- bring up the game ----------
        self._mame_process = self._launch_mame()

        # ---------- accept the command connection ----------
        deadline = time.monotonic() + self._ipc_config.connection_timeout
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Timed out waiting for command connection")
        self._command_socket.settimeout(remaining)
        self._command_connection, address = self._command_socket.accept()
        print(f"[MameOperator] Command connection accepted from {address[0]}:{address[1]}")

        print("[MameOperator] Ready")

    def stop(self) -> None:
        """Close IPC channels and terminate the MAME subprocess."""

        # ---------- close command channel ----------
        if self._command_connection is not None:
            try:
                self._command_connection.close()
            except OSError:
                pass
        if self._command_socket is not None:
            try:
                self._command_socket.close()
            except OSError:
                pass

        # ---------- close state FIFO ----------
        if self._state_fd is not None:
            try:
                os.close(self._state_fd)
            except OSError:
                pass
            self._remove_stale_fifo()

        # ---------- shut down the game ----------
        if self._mame_process is not None and self._mame_process.poll() is None:
            self._mame_process.terminate()
            try:
                self._mame_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._mame_process.kill()
                self._mame_process.wait()

        # ---------- clear the board ----------
        self._command_socket = None
        self._command_connection = None
        self._state_fd = None
        self._mame_process = None
        self._receive_buffer = b""
        self._last_frame = None
        self._last_command_text = ""
        self._last_maze = None
        self._last_creatures = None
        self._last_objects = None

    # ---------- communication ----------

    def recv(self) -> DaggorathState:
        """Block until the next tagged record arrives, returning current state.

        The returned DaggorathState always carries the latest known numeric
        state and the latest known command text. Records omit the unchanged
        half, so this method reconstructs from the last-known values.
        """
        while True:
            if self._state_fd is None:
                raise ConnectionError("Operator not started or already stopped")

            # ---------- parse a complete record when buffered ----------
            record = self._extract_record()
            if record is not None:
                return self._parse_record(record)

            # ---------- wait for the FIFO to become readable ----------
            readable, _, _ = select.select([self._state_fd], [], [], _STATE_READ_TIMEOUT)
            if not readable:
                raise TimeoutError("Timed out waiting for a state record")

            # ---------- read more bytes from the FIFO ----------
            try:
                chunk = os.read(self._state_fd, 4096)
            except OSError:
                raise ConnectionError("MAME disconnected (FIFO read error)")
            if not chunk:
                raise ConnectionError("MAME disconnected (EOF)")
            self._receive_buffer += chunk

    def send(self, command: commands.DaggorathCommand) -> None:
        """Send a command index (one byte) to MAME on the command socket."""

        if self._command_connection is None:
            raise ConnectionError("Operator not started or already stopped")

        payload = bytes([command.index])
        try:
            self._command_connection.sendall(payload)
        except OSError as exc:
            raise ConnectionError(f"Failed to send command: {exc}")

    # ---------- internals ----------

    def _extract_record(self) -> Optional[bytes]:
        """Return a complete record if one is buffered, else None.

        The first byte of the buffer is the record tag; its length is fixed
        per tag. Consumes the record from the buffer on success.
        """
        if not self._receive_buffer:
            return None

        tag = self._receive_buffer[0:1]
        length = _RECORD_LENGTHS.get(tag)
        if length is None:
            # Unknown tag — drop the byte and keep going.
            self._receive_buffer = self._receive_buffer[1:]
            return None

        if len(self._receive_buffer) < length:
            return None

        record = self._receive_buffer[:length]
        self._receive_buffer = self._receive_buffer[length:]
        return record

    def _parse_record(self, record: bytes) -> DaggorathState:
        """Parse a tagged record into a DaggorathState carrying current state.

        Each record carries only the channel(s) that changed; the rest are
        reconstructed from the last-known values.
        """
        tag = record[0:1]

        frame = self._last_frame
        command_text = self._last_command_text
        maze = self._last_maze
        creatures = self._last_creatures
        objects = self._last_objects

        if tag in (b"S", b"B"):
            frame = record[1:1 + FRAME_LEN]

        if tag in (b"T", b"B"):
            offset = 1 + (FRAME_LEN if tag == b"B" else 0)
            com_color = record[offset]
            pixels = record[offset + 1:offset + 1 + PIXEL_BYTES]
            command_text = decode_command_area(pixels, com_color)

        if tag == b"M":
            maze = record[1:1 + MAZE_BYTES]
        elif tag == b"C":
            creatures = record[1:1 + CREATURE_BYTES]
        elif tag == b"O":
            objects = record[1:1 + OBJECTS_BYTES]

        if frame is None:
            raise ConnectionError("Received a record before any numeric state")

        self._last_frame = frame
        self._last_command_text = command_text
        self._last_maze = maze
        self._last_creatures = creatures
        self._last_objects = objects
        return DaggorathState(
            frame,
            command_text=command_text,
            maze=maze,
            creatures=creatures,
            objects=objects,
        )

    def _remove_stale_fifo(self) -> None:
        """Remove a stale FIFO file if it exists."""
        fifo_path = self._ipc_config.state_fifo_path
        if os.path.exists(fifo_path):
            os.unlink(fifo_path)

    def _create_listening_socket(self, port: int) -> socket.socket:
        """Create a TCP socket, bind it, and begin listening."""
        host = self._ipc_config.command_host
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen(1)
        print(f"[MameOperator] Command socket listening on {host}:{port}")
        return server

    def _launch_mame(self) -> subprocess.Popen:
        """Spawn the MAME subprocess and return the Popen handle."""

        config = self._mame_config

        # ---------- prepare the scratch directory ----------
        mame_scratch_directory = os.path.join(PROJECT_PATH, ".mame")
        os.makedirs(mame_scratch_directory, exist_ok=True)

        # ---------- assemble the command ----------
        command_line = [
            "mame", "coco3", "daggorath",
            "-rompath", ROM_PATH,
            "-hashpath", HASH_PATH,
            "-pluginspath", PLUGINS_PATH,
            "-plugin", config.plugin_name,
            "-cfg_directory", mame_scratch_directory,
            "-skip_gameinfo",
            "-nonvram_save",
            "-sound", config.sound,
        ]
        if config.window:
            command_line.append("-window")

        # ---------- fire it up ----------
        env = os.environ.copy()
        env["STATE_FIFO_PATH"] = self._ipc_config.state_fifo_path
        env["COMMAND_HOST"] = self._ipc_config.command_host
        env["COMMAND_PORT"] = str(self._ipc_config.command_port)
        print(f"[MameOperator] Launching: {' '.join(command_line)}")
        return subprocess.Popen(command_line, env=env)