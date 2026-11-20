# Computational & Proof Artifacts (`work/`)

Place all code, symbolic derivations, formal proof files (`.lean`), Z3 scripts, notebooks, or verification scripts for this lead here.

Guidelines:
- Keep scripts self-contained and runnable from the lead root via `uv run rpipe run <lead-path> -- python work/<script>.py`.
- Emit a concise `summary.json` via `rpipe.helpers.io.save_summary(...)` when running experiments.
- Add automated unit/invariant tests (`test_*.py`) or register custom checks under `verification.checks` in `lead.yaml`.
