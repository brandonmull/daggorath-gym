# Deployment

_See [overview.md](../overview.md) for project context and architecture._

## Purpose

The environment is a library, not an application. Deployment answers one question: how does a trainer — ours or a stranger's — obtain, discover, configure, and run the environment, and where does the training code live relative to it? It prescribes how the environment is packaged and handed off, not how anyone trains.

## Repository layout

The workspace is a parent folder holding two independent repositories, each with its own git history and dependency set:

- **`daggorath-gym`** — the environment. Depends on `gymnasium` and `numpy` only; imports no training library.
- **`daggorath-agent`** — the training harness. Depends on `stable-baselines3`, `torch`, and `sb3-contrib`; consumes `daggorath_gym` as a library.

The two sit side by side so the environment stays free of training dependencies, while the training code — algorithms, sweeps, checkpoints — evolves without touching the environment.

## The environment repo

**Packaging.** The environment installs as a normal editable package through `pyproject.toml`. Nothing in the package imports a training library; the `gymnasium` dependency is the environment's own framework, not a trainer.

**Registration.** Importing the package registers `Daggorath-v0`, making the environment discoverable through `gymnasium.make` — the interface every RL tool uses to find a custom environment. Registration is a side effect of import, not a separate step.

**Reward.** The environment is the objective world: its step returns a placeholder reward. The real reward is a separate, agent-side choice. `DaggorathRewardWrapper` ships the project's default reward; a trainer may instead write its own wrapper that reads true state through the environment's `current_state` property. The environment stays a reporter and the reward stays a valuation, per `reward/plan.md`.

**Configuration.** `MameConfig` and `IpcConfig` select window and sound, the state FIFO path, and the command port. They flow through `gymnasium.make` keyword arguments, so a headless trainer configures the environment without editing code.

## The training repo

**Dependencies.** `stable-baselines3`, `torch`, `sb3-contrib`.

**Pipeline.**

```
train()
    → constructs the environment headless
    → applies the reward wrapper
    → wraps it in a vector environment
    → trains PPO
```

**Observation handling.** The observation is a Dict of a two-plane image (`map`) and flat entity and scalar arrays. A custom feature extractor routes the map plane through a convolutional network and the remaining channels through a multi-layer perceptron, then concatenates — the "CNN + MLP" split the perception plan describes.

**Action masking.** The factored action space (26 templates × 31 object specifiers) carries a joint constraint: the INCANT template accepts only the nine ring specifiers. SB3's per-axis masking cannot express a joint constraint, so a joint-mask policy belongs here, in the training repo. The environment keeps a no-op fallback, so a trainer that does not mask still runs correctly — it just wastes the occasional step. The first trainer may rely on that fallback with plain PPO, adding the joint-mask policy as its first refinement.

**Role.** The training repo is the reference implementation: a working end-to-end trainer that an external user reads and adapts to their own stack.

## Consumption

```
consume()
    → installs the environment package
    → imports it, which registers the id
    → obtains the environment through gymnasium.make
    → wraps it in a reward — the shipped one or a custom one
    → trains with the trainer's own stack
```

## Decisions

- The reward wrapper stays in the environment repo: it is gymnasium-only and algorithm-agnostic — task definition, not a trainer.
- Joint action masking lives in the training repo as a custom policy; the environment keeps the no-op fallback for invalid pairs.
- Registration exposes the raw environment only. The reward wrapper is an explicit opt-in, never a second registered id — the world and its worth stay separate.
- PPO is the first algorithm.

## Reference Documents

| Document | What It Contains |
|----------|-----------------|
| `README.md` | Installation, known issues, layout |
| `docs/plans/reward/plan.md` | The reward wrapper and the fact-vs-valuation split |
| `docs/plans/perception/plan.md` | The observation channels and the CNN + MLP split |
| `docs/plans/overview.md` | Project context and architecture |
