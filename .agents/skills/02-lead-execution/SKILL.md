---
name: 02-lead-execution
description: >-
  Stage 2 of the research pipeline: translate an approved lead specification into clean
  computational, symbolic, formal-proof, or derivation artifacts inside work/, and execute
  them through rpipe run for full provenance capture.
---

# Stage 2: Lead Execution (Code, Math, Proofs & Artifacts)

Use this skill after `lead.yaml` and `notes/01_background.md` are approved (or during Stage 2 <-> Stage 3 autonomous iteration).

## Objective

Produce the cleanest, smallest, most trustworthy artifact(s) inside `work/` that directly test or prove the lead's hypothesis, and execute them reproducibly with compact, LLM-readable outputs.

## Procedure

### 1. Select the Right Artifact Modality & Craft Skill
Do **not** default to brute-force numerics when a symbolic check or Z3 counterexample search answers the question faster and more definitively. Load the matching craft skill(s) before writing code:
- Numerical simulation / sweeps / plotting -> `craft-numerical-simulation`
- Symbolic derivations / algebra / analytic limits -> `craft-symbolic-math`
- Formal proofs / SMT counterexample search -> `craft-formal-proofs`
- Analytical derivations / literature notes -> `craft-research-and-derivations`

Before writing new utilities, check `src/rpipe/shared/` to see if a verified reusable primitive already exists.

### 2. Design Clean Artifacts in `work/`
Follow these structural rules:
- **No forced boilerplate**: Write idiomatic, readable Python scripts, SymPy modules, Lean 4 files, or LaTeX notes directly inside `work/`.
- **Deterministic by default**: Read the seed from environment variable `RPIPE_SEED` (set automatically by `rpipe run`) or CLI `--seed` and seed NumPy/Python/JAX PRNGs explicitly.
- **Respect `RPIPE_RUN_DIR`**: When launched via `rpipe run`, the environment variable `RPIPE_RUN_DIR` points to the current immutable run directory (`runs/<run_id>/`). Save plots, data arrays, and `summary.json` into `RPIPE_RUN_DIR` using `rpipe.helpers.io`:
  ```python
  from rpipe.helpers.io import get_run_dir, save_summary, log_metric
  ```
- **Keep stdout clean and `summary.json` compact**: Put key scalar metrics, convergence orders, invariant errors, proof statuses, and artifact filenames in `summary.json` so Stage 4 (and future LLM turns) can inspect results without reading megabytes of raw logs.
- **Separate core math from plotting/CLI**: Put core equations/solvers in importable functions inside `work/` so `pytest` and verification scripts can import and test them directly.

### 3. Execute via `rpipe run`
Mark the lead as `running` and execute every meaningful run through `rpipe run` (not raw `python`, except for quick interactive debugging):
```bash
uv run rpipe set-status projects/<project>/leads/<lead-id> running
uv run rpipe run projects/<project>/leads/<lead-id> --tag baseline --seed 42 -- python work/simulate.py
```
`rpipe run` automatically captures:
- `runs/<run_id>/manifest.json` (git SHA, dirty flag, command, seed, exit code, duration, Python/package versions)
- `runs/<run_id>/stdout.log` and `stderr.log`
- `runs/<run_id>/summary.json` (written by your script)
- Appends a compact record to `runs/ledger.jsonl`

### 4. Prototype Small Before Scaling Sweeps
1. Run a tiny fast case first (coarse grid / short time horizon / small $N$) to confirm the script completes cleanly and emits a valid `summary.json`.
2. Proceed immediately to Stage 3 (`03-scientific-verification`) to verify invariants and convergence **before** running expensive parameter sweeps.

## Anti-Patterns to Avoid
- Dumping giant matrices or thousands of lines to stdout.
- Hardcoding absolute machine paths inside `work/` scripts (always resolve paths relative to the lead directory or `RPIPE_RUN_DIR`).
- Overwriting previous run outputs in place — always let `rpipe run` create a fresh immutable run directory.
- Putting experimental lead-specific code into `src/rpipe/` prematurely.
