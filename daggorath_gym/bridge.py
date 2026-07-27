"""TCP bridge between Python and MAME's Lua emu.file sockets.

Encapsulates all MAME lifecycle and socket communication behind a
simple start/recv/send/close API.  Two unidirectional sockets mirror
the two-socket architecture proven in the sandbox:

    Port 15000  MAME (emu.file "w") --> Python  (game state)
    Port 15001  Python               --> MAME    (action commands)

Based on the patterns tested and documented in sandbox/.
"""

import json
import os
import socket
import subprocess
import sys
from typing import Any, Dict, Optional

from .paths import ROOT_PATH, EMU_PATH

# ---- defaults (mirrors emu/paths.lua) ---------------------------------------
DEFAULT_HOST = "127.0.0.1"
DEFAULT_STATE_PORT = 15000
DEFAULT_ACTION_PORT = 15001
DEFAULT_TIMEOUT = 30  # seconds to wait for MAME to connect
DEFAULT_SCRIPT = os.path.join(ROOT_PATH, "emulation", "autoboot.lua")


class MameBridge:
    """Manages a MAME subprocess and two-socket TCP communication."""

    def __init__(
        self,
        rompath: Optional[str] = None,
        hashpath: Optional[str] = None,
        lua_script: Optional[str] = None,
        host: str = DEFAULT_HOST,
        state_port: int = DEFAULT_STATE_PORT,
        action_port: int = DEFAULT_ACTION_PORT,
        timeout: float = DEFAULT_TIMEOUT,
        sound: str = "sdl",
        window: bool = True,
    ) -> None:
        self._host = host
        self._state_port = state_port
        self._action_port = action_port
        self._timeout = timeout

        # Absolute paths – relative ones fail when MAME changes CWD
        self._rompath = rompath or os.path.join(ROOT_PATH, "emulation", "roms")
        self._hashpath = hashpath or os.path.join(ROOT_PATH, "emulation", "hash")
        self._lua_script = lua_script or os.path.join(ROOT_PATH, "emulation", "autoboot.lua")

        self._sound = sound
        self._window = window

        # Internal state
        self._state_sock: Optional[socket.socket] = None
        self._action_sock: Optional[socket.socket] = None
        self._state_conn: Optional[socket.socket] = None
        self._action_conn: Optional[socket.socket] = None
        self._mame_process: Optional[subprocess.Popen] = None
        self._recv_buf = b""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Bind TCP servers, launch MAME, accept both connections."""
        self._bind()
        self._launch_mame()
        self._accept()

    def recv(self) -> Dict[str, Any]:
        """Block until the next JSON state message arrives from MAME.

        Returns the parsed dictionary, e.g.
            {"event":"observerTriggered","heartCounter":100,...}
        """
        while True:
            # Check if we already have a complete line buffered
            if b"\n" in self._recv_buf:
                line, self._recv_buf = self._recv_buf.split(b"\n", 1)
                if line.strip():
                    return json.loads(line.decode("utf-8"))
                continue

            # Read more data from the state socket
            if self._state_conn is None:
                raise ConnectionError("Bridge not started or already closed")

            try:
                chunk = self._state_conn.recv(4096)
            except ConnectionResetError:
                raise ConnectionError("MAME disconnected (connection reset)")

            if not chunk:
                raise ConnectionError("MAME disconnected (EOF)")

            self._recv_buf += chunk

    def send(self, data: Dict[str, Any]) -> None:
        """Send a JSON action command to MAME on the action socket."""
        if self._action_conn is None:
            raise ConnectionError("Bridge not started or already closed")

        payload = (json.dumps(data) + "\n").encode("utf-8")
        try:
            self._action_conn.sendall(payload)
        except OSError as exc:
            raise ConnectionError(f"Failed to send action: {exc}")

    def close(self) -> None:
        """Shut down MAME and close all sockets."""
        for conn in (self._state_conn, self._action_conn):
            if conn:
                try:
                    conn.close()
                except OSError:
                    pass
        for sock in (self._state_sock, self._action_sock):
            if sock:
                try:
                    sock.close()
                except OSError:
                    pass

        if self._mame_process is not None and self._mame_process.poll() is None:
            self._mame_process.terminate()
            try:
                self._mame_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._mame_process.kill()
                self._mame_process.wait()

        self._state_sock = None
        self._action_sock = None
        self._state_conn = None
        self._action_conn = None
        self._mame_process = None
        self._recv_buf = b""

    def is_running(self) -> bool:
        """Return True if MAME is still running and sockets are open."""
        return (
            self._mame_process is not None
            and self._mame_process.poll() is None
            and self._state_conn is not None
            and self._action_conn is not None
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _bind(self) -> None:
        """Create and bind the two TCP server sockets."""
        self._state_sock = _create_server(self._host, self._state_port)
        self._action_sock = _create_server(self._host, self._action_port)

    def _launch_mame(self) -> None:
        """Spawn MAME as a subprocess with the Lua autoboot script."""
        cmd = _build_mame_cmd(
            rompath=self._rompath,
            hashpath=self._hashpath,
            script=self._lua_script,
            sound=self._sound,
            window=self._window,
        )
        print(f"[MameBridge] Launching: {' '.join(cmd)}")
        self._mame_process = subprocess.Popen(cmd)

    def _accept(self) -> None:
        """Accept connections from MAME's Lua client on both sockets."""
        if self._state_sock is None or self._action_sock is None:
            raise RuntimeError("Sockets not bound — call _bind() first")

        self._state_sock.settimeout(self._timeout)
        self._action_sock.settimeout(self._timeout)

        print(f"[MameBridge] Waiting for state connection on {self._state_port}...")
        self._state_conn, state_addr = self._state_sock.accept()
        print(f"[MameBridge] State connected from {state_addr[0]}:{state_addr[1]}")

        print(f"[MameBridge] Waiting for action connection on {self._action_port}...")
        self._action_conn, action_addr = self._action_sock.accept()
        print(f"[MameBridge] Action connected from {action_addr[0]}:{action_addr[1]}")

    def __enter__(self) -> "MameBridge":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):  # type: ignore
        self.close()
        return False


# ----------------------------------------------------------------------
# Module-level helpers (kept private so the public API stays clean)
# ----------------------------------------------------------------------

def _create_server(host: str, port: int) -> socket.socket:
    """Return a listening TCP socket bound to *host*:*port*."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((host, port))
    except OSError as exc:
        print(
            f"ERROR: Could not bind {host}:{port} — {exc}", file=sys.stderr
        )
        raise
    sock.listen(1)
    print(f"[MameBridge] Listening on {host}:{port}")
    return sock


def _build_mame_cmd(
    rompath: str,
    hashpath: str,
    script: str,
    sound: str,
    window: bool,
) -> list:
    """Build the MAME command line."""
    cmd = [
        "mame", "coco3", "daggorath",
        "-rompath", rompath,
        "-hashpath", hashpath,
        "-autoboot_script", script,
        "-skip_gameinfo",
        "-nonvram_save",
        "-sound", sound,
    ]
    if window:
        cmd.append("-window")
    return cmd
