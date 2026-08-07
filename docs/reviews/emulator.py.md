# emulator.py — Design Review

_8 Aug 2026 — Brandon & Cline_

This records observations, concerns, alternatives, and decisions from a line-by-line review of `daggorath_gym/emulator.py` (`MameOperator` class). The file manages the MAME subprocess lifecycle and TCP socket communication between Python and Lua.

---

## 1. `config.py` duplication

**Observation:** Two MAME command builders existed: `_build_mame_cmd()` in `emulator.py` and `cmd`/`get_cmd()` in `config.py`. `config.py` was imported nowhere — dead code.

**Decision:** Delete `config.py`. `_launch_mame()` is the single source of truth for MAME command-line construction.

---

## 2. Constant names (`paths.py`)

**Observation:** `ROOT_PATH`, `EMU_PATH`, `MAME_CFG_DIR` — abbreviated, ambiguous, and leaking MAME implementation details. `EMU` violates the project's "fully-worded terminology" convention. `MAME_CFG_DIR` is obscure jargon for "MAME's auto-generated config directory."

**Alternatives considered:**

- `PROJECT_PATH`, `EMULATION_PATH` — consistent `_PATH` suffix for filesystem paths
- `MAME_CFG_DIR` eliminated entirely — replaced by an inlined `.mame/` scratch directory in `_launch_mame()` with a comment explaining its purpose

**Decision:** `PROJECT_PATH`, `EMULATION_PATH`. Drop `MAME_CFG_DIR` — the `.mame/` directory is created on demand in `_launch_mame()` with an explanatory comment.

---

## 3. `DEFAULT_` prefix → `SocketConfig` / `MameConfig` dataclasses

**Observation:** Five module-level constants with `DEFAULT_` prefix (`DEFAULT_HOST`, `DEFAULT_STATE_PORT`, etc.). "Default" promises an override mechanism that doesn't exist yet — aspirational naming.

**Alternatives considered:**

- Drop the prefix (bare `HOST`, `STATE_PORT`) — still loose constants
- Group into a dict — adds structure but no type safety
- Frozen dataclasses — typed, documented, overridable at construction time, grouped by concern

**Decision:** Two frozen dataclasses: `SocketConfig` (listen_host, state_port, command_port, connection_timeout) and `MameConfig` (rom_path, hash_path, autoboot_script_path, sound, window). `MameOperator.__init__` accepts either/both with sensible defaults. This separates socket parameters from process parameters naturally — they're independent config namespaces that may diverge (e.g., parallel training needs different ports, testing needs different autoboot scripts).

**Naming notes:**
- `listen_host` — inside `SocketConfig`, the namespace provides context: "the host the socket configuration listens on"
- `autoboot_script_path` — fully-worded, follows the `_PATH` convention for filesystem paths

---

## 4. Abbreviated names

**Observation:** `_state_conn`, `_command_conn`, `_recv_buf` — abbreviations violate the fully-worded terminology convention.

**Decision:** `_state_connection`, `_command_connection`, `_receive_buffer`. Also: `connected_socket` and `listening_socket` as iteration variables in `stop()` rather than the inconsistent `connection`/`server_socket` pairing.

---

## 5. Under-descriptive method names

**Observation:** `_bind()`, `_accept()`, `_create_server()` — verbs without objects, unclear what they operate on. Also, `_bind` and `_accept` were wrappers that operated on two sockets collectively, hiding the per-socket lifecycle.

**Alternatives considered:**

- Per-socket methods: `_create_listening_socket(port)` and `_wait_for_connection(socket, timeout)` with a callback — gets complicated when both sockets need to connect
- Combined create+wait: `_open_connection(port)` — violates ordering (MAME must launch between create and wait)
- Batch accept: `_wait_for_connections(sockets, timeout)` — handles all sockets at once, all-or-nothing

**Decision:** `_create_listening_socket(host, port)` creates a single listening socket and returns it. `_wait_for_connections(sockets, timeout)` takes all listening sockets and returns all connected sockets in order. `start()` explicitly shows the three phases: create sockets → launch MAME → wait for connections. Each socket is handled independently during creation; the batch wait acknowledges that the bridge is unusable unless all connections succeed.

`_launch_mame()` now returns the `Popen` handle rather than assigning to `self._mame_process` — the helper builds and launches, the caller (`start()`) owns the result. Clean separation of concerns.

---

## 6. `start`/`close` asymmetry → `start`/`stop`

**Observation:** `start()` paired with `close()` — asymmetry implies different abstractions (starting a service vs closing a file handle).

**Decision:** `start()` / `stop()`. Matches the service/process lifecycle metaphor.

---

## 7. `__enter__` / `__exit__` context manager methods

**Observation:** Enabled `with MameOperator() as operator:` syntax, but no code in the project used it. Speculative API surface.

**Decision:** Remove both methods. Callers explicitly call `start()` and `stop()`.

---

## 8. Readability and formatting

**Observations:**

- **Compacted statements** — tuple unpack + method call combined on one line made code dense. Expanded: assign result to a local, then unpack.
- **Inconsistent comment use** — some blocks had section dividers, others didn't, creating an expectation of comments that wasn't consistently met.
- **`stop()` indentation** — `for connection → if connection → try` created three levels of nesting for a simple close-with-suppression pattern. Flattened with `if connection is None: continue`.
- **`chunk`** — kept as-is; idiomatic in socket code for "piece of a stream."

**Decisions:** Expanded compacted statements. Consistent `# ---- Section ----` dividers for major logical groups (Configuration, Lifecycle, Communication, Internal, Socket helpers). Flattened nested loops in `stop()`. Consistent iteration variable naming (`connected_socket`, `listening_socket`).

---

## Deferred

| Topic | When |
|-------|------|
| Parallel accept via `select.select()` | When sequential accept becomes a bottleneck or Lua ordering changes — the `_wait_for_connections` signature already supports it |
| Print logging control | When headless training makes prints noisy — currently dev scaffolding |
| MAME configuration flow from env to operator | See review-env.md #9 — open question about `__init__` vs `reset(options=...)` |
