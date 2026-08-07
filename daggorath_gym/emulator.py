"""MAME operator — lifecycle management and socket communication.

Encapsulates the MAME subprocess and two-way TCP communication behind
a simple start/stop/recv/send API. Two unidirectional sockets:

    Port 15000  MAME (emu.file "w") --> Python  (game state)
    Port 15001  Python               --> MAME    (command dispatch)
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
class SocketConfig:
    """Parameters for the two TCP sockets between Python and MAME."""
    listen_host: str = "127.0.0.1"
    state_port: int = 15000
    command_port: int = 15001
    connection_timeout: float = 30


@dataclass(frozen=True)
class MameConfig:
    """Parameters for the MAME subprocess."""
    rom_path: str = os.path.join(PROJECT_PATH, "emulation", "roms")
    hash_path: str = os.path.join(PROJECT_PATH, "emulation", "hash")
    autoboot_script_path: str = os.path.join(EMULATION_PATH, "autoboot.lua")
    sound: str = "sdl"
    window: bool = True


# ---------- MameOperator ----------

class MameOperator:
    """Operates a MAME subprocess and communicates with it over TCP."""

    def __init__(
        self,
        mame_config: Optional[MameConfig] = None,
        socket_config: Optional[SocketConfig] = None,
    ) -> None:
        # ---------- what to run and how to connect ----------
        self._mame_config = mame_config or MameConfig()
        self._socket_config = socket_config or SocketConfig()

        # ---------- the emulator itself ----------
        self._mame_process: Optional[subprocess.Popen] = None

        # ---------- the receiver ----------
        self._state_socket: Optional[socket.socket] = None
        self._state_connection: Optional[socket.socket] = None
        self._receive_buffer = b""

        # ---------- the transmitter ----------
        self._command_socket: Optional[socket.socket] = None
        self._command_connection: Optional[socket.socket] = None

    # ---------- lifecycle ----------

    def start(self) -> None:
        """Create listening sockets, launch MAME, and wait for both connections."""

        # ---------- raise the antennae ----------
        self._state_socket = self._create_listening_socket(self._socket_config.state_port)
        self._command_socket = self._create_listening_socket(self._socket_config.command_port)

        # ---------- bring up the game ----------
        self._mame_process = self._launch_mame()

        # ---------- lock in the signal ----------
        connections = self._wait_for_connections([self._state_socket, self._command_socket])
        self._state_connection = connections[0]
        self._command_connection = connections[1]

        print("[MameOperator] Ready — receiving game state, accepting commands")

    def stop(self) -> None:
        """Close sockets and terminate the MAME subprocess."""

        # ---------- drop the signal ----------
        for connected_socket in (self._state_connection, self._command_connection):
            if connected_socket is None:
                continue
            try:
                connected_socket.close()
            except OSError:
                pass
        for listening_socket in (self._state_socket, self._command_socket):
            if listening_socket is None:
                continue
            try:
                listening_socket.close()
            except OSError:
                pass

        # ---------- shut down the game ----------
        if self._mame_process is not None and self._mame_process.poll() is None:
            self._mame_process.terminate()
            try:
                self._mame_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._mame_process.kill()
                self._mame_process.wait()

        # ---------- clear the board ----------
        self._state_socket = None
        self._command_socket = None
        self._state_connection = None
        self._command_connection = None
        self._mame_process = None
        self._receive_buffer = b""

    # ---------- communication ----------

    def recv(self) -> DaggorathState:
        """Block until the next raw byte state frame arrives from MAME."""

        while True:
            if b"\n" in self._receive_buffer:
                line, self._receive_buffer = self._receive_buffer.split(b"\n", 1)
                return DaggorathState(line)

            if self._state_connection is None:
                raise ConnectionError("Operator not started or already stopped")

            # ---------- read from the wire ----------
            try:
                chunk = self._state_connection.recv(4096)
            except ConnectionResetError:
                raise ConnectionError("MAME disconnected (connection reset)")
            if not chunk:
                raise ConnectionError("MAME disconnected (EOF)")
            self._receive_buffer += chunk

    def send(self, command: commands.DaggorathCommand) -> None:
        """Send a command index (one byte) to MAME on the command socket."""

        if self._command_connection is None:
            raise ConnectionError("Operator not started or already stopped")

        # ---------- transmit a command ----------
        payload = bytes([command.index])
        try:
            self._command_connection.sendall(payload)
        except OSError as exc:
            raise ConnectionError(f"Failed to send command: {exc}")

    # ---------- internals ----------

    def _create_listening_socket(self, port: int) -> socket.socket:
        """Create a TCP socket, bind it, and begin listening."""
        host = self._socket_config.listen_host
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen(1)
        print(f"[MameOperator] Listening on {host}:{port}")
        return server

    def _wait_for_connections(self, listening_sockets: list) -> list[socket.socket]:
        """Block until every listening socket has an accepted connection.

        Returns:
            Connected sockets in the same order as listening_sockets.

        Raises:
            TimeoutError: If not all sockets connect within the timeout.
        """
        deadline = time.monotonic() + self._socket_config.connection_timeout
        connected = [None] * len(listening_sockets)

        for index, server_socket in enumerate(listening_sockets):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    f"Timed out waiting for connection {index + 1} of {len(listening_sockets)}"
                )
            server_socket.settimeout(remaining)
            connection, address = server_socket.accept()
            connected[index] = connection
            print(f"[MameOperator] Accepted connection from {address[0]}:{address[1]}")

        return connected

    def _launch_mame(self) -> subprocess.Popen:
        """Spawn the MAME subprocess and return the Popen handle."""
        
        config = self._mame_config

        # ---------- prepare the scratch directory ----------
        mame_scratch_directory = os.path.join(PROJECT_PATH, ".mame")
        os.makedirs(mame_scratch_directory, exist_ok=True)

        # autoboot_delay must be at least 1 so the CoCo input buffer
        # is ready by the time commands.lua posts its priming carriage returns.
        autoboot_delay = 1

        # ---------- assemble the command ----------
        command_line = [
            "mame", "coco3", "daggorath",
            "-rompath", config.rom_path,
            "-hashpath", config.hash_path,
            "-autoboot_script", config.autoboot_script_path,
            "-autoboot_delay", str(autoboot_delay),
            "-cfg_directory", mame_scratch_directory,
            "-skip_gameinfo",
            "-nonvram_save",
            "-sound", config.sound,
        ]
        if config.window:
            command_line.append("-window")

        # ---------- fire it up ----------
        env = os.environ.copy()
        env["SOCKET_LISTEN_HOST"] = self._socket_config.listen_host
        env["SOCKET_STATE_PORT"] = str(self._socket_config.state_port)
        env["SOCKET_COMMAND_PORT"] = str(self._socket_config.command_port)
        print(f"[MameOperator] Launching: {' '.join(command_line)}")
        return subprocess.Popen(command_line, cwd=EMULATION_PATH, env=env)
