# env.py — Implemented Decisions

_8 Aug 2026_

This records the concrete code changes applied to `daggorath_gym/env.py` during the post-build review. For the full analysis, see `docs/reviews/env.md`.

## Applied Changes

### `_compute_reward` — raises `NotImplementedError`

Placeholder heartbeat calculation (`heart_beat_interval / 255.0`) replaced. That calculation was actively misleading — it rewards "stay calm" in a game where combat raises heart rate. The method now raises `NotImplementedError` to signal that reward design is required before training can proceed.

### `_check_terminated` — raises `NotImplementedError`

Partial wizard-dead check (`evil_wizard_dead == 0xFF`) replaced. The detection was unvalidated (does the byte persist? does the game restart on death?) and looked complete enough to use, masking the need for design work. Now raises `NotImplementedError` — same policy as reward.

### `_check_truncated` — added, raises `NotImplementedError`

Previously `truncated = False` was set inline in `step()` with no dedicated method. A new `_check_truncated(self, state)` method raises `NotImplementedError`. While truncation is typically handled by gymnasium's `TimeLimit` wrapper, the decision point should be explicit and follow the same design signal as reward and termination.

### Docstring — class-specific

Module docstring stays broad ("Gymnasium environment for Dungeons of Daggorath"). Class docstring now describes spaces (Discrete(154), Box(12, uint16)), lifecycle (owns MameOperator), and current status (reward/termination raise NotImplementedError). No duplication.

### `@staticmethod` removed

`_compute_reward` and `_check_terminated` were `@staticmethod` — no `self`. Now regular instance methods. When implemented, they may need instance state (history, episode context).

### `step()` — fully typed

Signature updated to `step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict]` matching gymnasium conventions.

### `reset()` — gymnasium-aligned signature

Changed from `**kwargs` to explicit `reset(self, *, seed=None, options=None)`. Returns `{"seed": seed}` in info dict per gymnasium convention. Seed not yet wired to an RNG.

---

_12 Aug 2026_

### `socket_config` → `ipc_config`

The `__init__` parameter renamed from `socket_config` to `ipc_config` and the import changed from `SocketConfig` to `IpcConfig`. Reflects the hybrid IPC architecture — the state channel is now a FIFO, not a TCP socket.
