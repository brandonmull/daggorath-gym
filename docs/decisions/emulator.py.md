# emulator.py — Implemented Decisions

_8 Aug 2026_

This records the concrete code changes applied to `daggorath_gym/emulator.py` (`MameOperator` class) during the post-build review. For the full analysis, see `docs/reviews/emulator.md`.

## Applied Changes

### `config.py` deleted

Two MAME command builders existed — `_build_mame_cmd()` in `emulator.py` and `cmd`/`get_cmd()` in `config.py`. `config.py` was dead code (imported nowhere). Deleted.

### `SocketConfig` and `MameConfig` dataclasses

Replaced five module-level `DEFAULT_` constants with two frozen dataclasses:

- **`SocketConfig`** — `listen_host`, `state_port`, `command_port`, `connection_timeout`
- **`MameConfig`** — `rom_path`, `hash_path`, `autoboot_script_path`, `sound`, `window`

The dataclass namespace provides context for names like `listen_host` (the host the socket configuration listens on). Separates socket parameters from process parameters — independent config namespaces that may diverge (parallel training needs different ports, testing needs different autoboot scripts).

### `paths.py` renamed

`ROOT_PATH` → `PROJECT_PATH`, `EMU_PATH` → `EMULATION_PATH`, `MAME_CFG_DIR` dropped entirely. MAME's auto-generated config files now go to a `.mame/` scratch directory created on demand in `_launch_mame()`.

### Abbreviated names expanded

`_state_conn` → `_state_connection`, `_command_conn` → `_command_connection`, `_recv_buf` → `_receive_buffer`. Iteration variables in `stop()` use `connected_socket` and `listening_socket`.

### Method names improved

- `_bind()` / `_accept()` → `_create_listening_socket(host, port)` + `_wait_for_connections(sockets, timeout)`
- `_launch_mame()` now returns `Popen` handle rather than assigning to `self` — caller (`start()`) owns the result
- `close()` → `stop()`

`start()` now explicitly shows three phases: create sockets → launch MAME → wait for connections.

### `is_running()` deleted

No internal code used it. Speculative API surface.

### `__enter__` / `__exit__` removed

Enabled `with MameOperator() as operator:` but no caller in the project used this pattern. Forces explicit `start()`/`stop()` lifecycle.

### `recv()` empty-line stripping removed

`if line.strip()` was silently discarding valid frames (e.g., all-null startup frames). Let `DaggorathState` schema validation catch malformed data.

### `-autoboot_delay` extracted to constant

Hardcoded `"1"` in `_build_mame_cmd()` extracted to a named local `autoboot_delay = 1` with a comment explaining why it must be at least 1 (CoCo input buffer readiness for priming carriage returns).

---

_12 Aug 2026_

### `SocketConfig` → `IpcConfig`

The state channel is no longer a TCP socket — it's a named pipe (FIFO). `SocketConfig` renamed to `IpcConfig` to reflect the hybrid architecture. `state_port` and `listen_host` fields dropped; replaced by `state_fifo_path` and `command_host`/`command_port`.

### `-autoboot_script` → `-plugin`

MAME launched with `-plugin` instead of `-autoboot_script`. The plugin path points to `emulation/plugins/daggorath/`. `-autoboot_delay` removed — the plugin's `startplugin()` entry point fires when the machine initializes, and the keyboard priming delay is handled by the 300-frame auto-prime in `commands.lua`.

### State channel: TCP socket → FIFO

`recv()` now reads from a FIFO via `os.read()` instead of a TCP socket `recv()`. `start()` creates the FIFO with `os.mkfifo()` and opens it `O_RDWR` before launching MAME. `stop()` removes the stale FIFO on cleanup. The command channel (`send()`) remains a TCP socket — `emu.file("r")` is documented stable and provides the non-blocking reads that FIFOs can't do.

### Formatting improvements

- Compacted statements expanded (tuple unpack + method call split across lines)
- `stop()` indentation flattened with `if x is None: continue`
- Consistent comment section dividers for major logical groups