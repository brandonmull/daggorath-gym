#!/usr/bin/env python3
"""Verify torch light end-to-end: PULL LEFT TORCH, USE LEFT, check RAM values.

Drives the production plugin through MameOperator (command channel + state
FIFO + screen decode) and reports the torch/light fields at each step.

The player starts with a PINE TORCH in the backpack (grammar line 97), so
PULL LEFT TORCH always has a torch to grab. Pine torch values (ROM DA84):
minutes 15, physical light 7, magic light 0.
"""

import sys
import time
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from daggorath_gym.commands import _COMMAND_PHRASES, DaggorathCommand
from daggorath_gym.emulator import MameOperator, IpcConfig

IPC = IpcConfig(state_fifo_path="/tmp/daggorath-torch-light", command_port=15401)

PULL_INDEX = _COMMAND_PHRASES.index("PULL LEFT TORCH")
USE_INDEX = _COMMAND_PHRASES.index("USE LEFT")


def _read_until(operator, predicate, max_records=100):
    """Read records until predicate(state) is true, the cap, or a read timeout."""
    seen = []
    for _ in range(max_records):
        try:
            state = operator.recv()
        except TimeoutError:
            break
        seen.append(state)
        if predicate(state):
            break
    return seen


def _print_torch_light(label, state):
    print(
        f"[{label}] torch_minutes={state.torch_minutes} "
        f"torch_physical_light={state.torch_physical_light} "
        f"torch_magic_light={state.torch_magic_light} "
        f"effective_light={state.effective_light:#x} "
        f"ambient_light={state.ambient_light:#x} "
        f"m0221={state.m0221:#x} "
        f"player_strength={state.player_strength:#x}"
    )


def main():
    operator = MameOperator(ipc_config=IPC)
    try:
        operator.start()

        print("=== Initial state (torch unlit) ===")
        initial = operator.recv()
        print(f"command area: {initial.command_text!r}")
        _print_torch_light("initial", initial)

        # ---- Step 1: PULL LEFT TORCH (torch moves backpack → left hand) ----
        print("\n=== Step 1: PULL LEFT TORCH ===")
        operator.send(DaggorathCommand(index=PULL_INDEX))
        pull_states = _read_until(
            operator, lambda s: "PULL" in s.command_text.upper()
        )
        pull_state = pull_states[-1]
        print(f"command area: {pull_state.command_text!r}")
        _print_torch_light("after PULL", pull_state)

        # Give PULL time to finish before posting the next command.
        time.sleep(1.5)

        # ---- Step 2: USE LEFT (light the torch) ----
        print("\n=== Step 2: USE LEFT ===")
        operator.send(DaggorathCommand(index=USE_INDEX))
        use_states = _read_until(operator, lambda s: s.torch_minutes > 0)
        lit_state = use_states[-1]
        print(f"command area: {lit_state.command_text!r}")
        _print_torch_light("after USE", lit_state)

        # effective_light is recomputed on the next display refresh.
        refresh_states = _read_until(
            operator, lambda s: s.effective_light == 0x0700, max_records=50
        )
        final = refresh_states[-1]
        _print_torch_light("after refresh", final)

        # ---- Checks ----
        print("\n=== Checks ===")
        checks = [
            ("torch_minutes in 14..15", 14 <= final.torch_minutes <= 15, final.torch_minutes),
            ("torch_physical_light == 7", final.torch_physical_light == 7, final.torch_physical_light),
            ("torch_magic_light == 0", final.torch_magic_light == 0, final.torch_magic_light),
            ("effective_light == 0x0700", final.effective_light == 0x0700, hex(final.effective_light)),
            ("ambient_light == 0", final.ambient_light == 0, final.ambient_light),
        ]
        failures = []
        for name, ok, got in checks:
            print(f"{'PASS' if ok else 'FAIL'}  {name}  (got {got})")
            if not ok:
                failures.append(name)

        if failures:
            print(f"\nRESULT: FAIL ({len(failures)} check(s))")
            return 1
        print("\nRESULT: PASS")
        return 0
    finally:
        operator.stop()


if __name__ == "__main__":
    sys.exit(main())
