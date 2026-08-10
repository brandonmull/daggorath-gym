# Command Readiness Sandbox

Determines exactly when Dungeons of Daggorath becomes ready for agent commands after
cold boot — purely from RAM signals, no visual processing.

## Quick Start

```bash
python sandbox/command-readiness/server.py
```

Automatically primes the keyboard at frame 300 (two `\r`) to trigger the demo→live transition.

## Architecture

```
sandbox/command-readiness/
├── plugin.json          # MAME plugin descriptor
├── init.lua             # Plugin: saves notifier subscriptions (GC fix), logs RAM every frame
├── server.py            # Python launcher — detached, reads log.txt
├── log.txt              # Frame-by-frame RAM trace (CSV)
├── frames.csv           # Old data (from earlier autoboot tests)
├── command-readiness.lua # Old autoboot script (superseded by plugin init.lua)
└── README.md            # This file
```

## Findings: The Transition Timeline

| Frame | gameMode | displayFunction | Event |
|-------|----------|-----------------|-------|
| 180–299 | 255 (0xFF) | 0,0 | Demo mode — boot delay window |
| **300** | 255 | 0,0 | **Keyboard auto-prime: two `\r` posted** |
| 301–312 | 255 | 0,0 | Game processes the Enter key |
| **313** | **0 (0x00)** | 0,0 | **gameMode flips to live!** Machine reset begins |
| 314–724 | 0 | 0,0 | Post-reset window: CoCo RAM rebuilding |
| **725** | **0** | **206,102 (0xCE66)** | **displayFunction → normal game screen** |
| 725–1619 | 0 | 206,102 | **Live play — ready for agent commands** |

**Key result:** The game becomes command-ready at **frame 725** (~12 seconds after cold boot, ~7 seconds after keyboard priming).

## RAM Signals Logged

| Signal | Address | Width |
|--------|---------|-------|
| gameMode | 0x0277 | 1 byte |
| inputHead | 0x02BC | 1 byte |
| inputTail | 0x02BD | 1 byte |
| displayFnLo | 0x02B2 | 1 byte |
| displayFnHi | 0x02B3 | 1 byte |