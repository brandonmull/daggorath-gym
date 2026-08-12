"""MAME operator — lifecycle management and hybrid IPC communication.

Encapsulates the MAME subprocess and two-channel IPC behind
a simple start/stop/recv/send API.

    State channel:   named pipe (FIFO) — MAME writes, Python reads
    Command channel: TCP socket         — Python writes, MAME reads
"""

import os
import socket
import subprocess
import time
from dataclasses import dataclass
from typing import Optional

from . import commands
from .paths import PROJECT_PATH, EMULATION_PATH
from .state import DaggorathState


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
    rom_path: str = os.path.join(PROJECT_PATH, "emulation", "roms")
    hash_path: str = os.path.join(PROJECT_PATH, "emulation", "hash")
    plugin_path: str = os.path.join(EMULATION_PATH, "plugins", "daggorath")
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

        # ---------- receive buffer ----------
        self._receive_buffer = b""

    # ---------- lifecycle ----------

    def start(self) -> None:
        """Create the state FIFO, open the command socket, launch MAME, and handshake."""

        # ---------- create the state FIFO ----------
        fifo_path = self._ipc_config.state_fifo_path
        self._remove_stale_fifo()
        os.mkfifo(fifo_path)
        self._state_fd = os.open(fifo_path, os.O_RDWR)
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

    # ---------- communication ----------

    def recv(self) -> DaggorathState:
        """Block until the next raw byte state frame arrives from MAME."""

        while True:
            if b"\n" in self._receive_buffer:
                line, self._receive_buffer = self._receive_buffer.split(b"\n", 1)
                return DaggorathState(line)

            if self._state_fd is None:
                raise ConnectionError("Operator not started or already stopped")

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
            "-rompath", config.rom_path,
            "-hashpath", config.hash_path,
            "-plugin", config.plugin_path,
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
        return subprocess.Popen(command_line, cwd=EMULATION_PATH, env=env)