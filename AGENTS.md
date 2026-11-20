# AI Research Pipeline — Agent Operating Manual (`AGENTS.md`)

This repository is a single-researcher, agent-native workspace for **theoretical mathematics and physics**. It is designed to scale across many concurrent **projects** and **leads** (ideas, conjectures, models, proofs) while keeping every lead isolated, scientifically verified, and honestly evaluated.

---

## 1. Repository Map

| Path | Role |
| :--- | :--- |
| `.agents/skills/` | Modular stage & craft `SKILL.md` playbooks. **Always load the relevant skill before acting.** |
| `inbox/` | Universal root drop-in zone for papers (`.pdf`, `.tex`, `.bib`), whiteboard photos, notebooks, or data files dropped before a project exists. File them into `projects/<project>/refs/` during Stage 1. |
| `projects/<project>/` | Broad research programs. Each holds `project.yaml`, `README.md`, `refs/` (shared project papers/files), and `leads/`. |
| `projects/<project>/leads/<lead-id>/` | Self-contained research lead with 5 zones: `lead.yaml`, `notes/`, `work/`, `runs/`, `evaluation.md`. |
| `src/rpipe/` | Thin CLI (`rpipe`) + lightweight verification/IO helpers. Do **not** bloat this with project-specific physics/math. |
| `src/rpipe/shared/` | Reusable, battle-tested math/physics primitives promoted out of verified leads. |
| `templates/` | Canonical templates copied by `rpipe init-project` and `rpipe new-lead`. |
| `tests/` | Core framework tests. |

---

## 2. The 4-Stage Pipeline & Skill Routing

Every independent idea progresses through 4 explicit stages. Load the matching skill in `.agents/skills/` at each stage:

1. **Stage 1 — Idea -> Clarify -> Research -> Spec** (`01-idea-to-spec`)
   - Check `uv run rpipe status --json` (which also reports any files waiting in `inbox/`).
   - Inspect any referenced papers/files in `inbox/` or `projects/<project>/refs/` (natively for multimodal PDFs/images, or via `uv run rpipe inspect-ref <path> [--pages 1-5]` across any IDE).
   - **Clarification Interview (Grill the Researcher)**: Before guessing missing mathematical/physical details, grill the researcher on every unresolved ambiguity (regime, conventions, boundary conditions, modality, falsification criteria, scope) — **one question at a time, with a recommended default for each** — skipping anything already answered by the workspace or dropped references (and skipping only if the researcher explicitly asked to proceed autonomously without questions).
   - Scaffold the project/lead (`uv run rpipe init-project` / `uv run rpipe new-lead`), **move** idea-related files from `inbox/` into `projects/<project>/refs/` (or `leads/<lead-id>/notes/` if single-lead-only), and record exact file/page/equation anchors in `lead.yaml` (`links.references`) and `notes/01_background.md`.
   - **Default Human Checkpoint**: Stop and present the `lead.yaml` spec and execution plan for researcher approval before writing heavy code or running long computations (unless the researcher explicitly asked to run end-to-end).

2. **Stage 2 — Execute / Compute / Prove** (`02-lead-execution`)
   - Choose the right artifact(s) inside `work/` (Python simulation, SymPy derivation, Z3/Lean 4 proof, LaTeX derivation, benchmark table, or figure script).
   - Also load the matching craft skill(s):
     - `craft-research-and-derivations` — background notes, LaTeX rigor, assumptions ledger.
     - `craft-numerical-simulation` — NumPy/SciPy/JAX integrators, stability, convergence, sweeps, plots.
     - `craft-symbolic-math` — SymPy derivations, dimensional analysis, numerical spot-checks.
     - `craft-formal-proofs` — Lean 4 (zero-`sorry`, axiom audit) and Z3/SMT proofs & counterexample search.
   - Execute computational scripts through `uv run rpipe run <lead_path> <script_or_cmd>` so every run records `manifest.json`, `summary.json`, git SHA, seed, and wall-clock timing under `runs/`.

3. **Stage 3 — Scientific Verification** (`03-scientific-verification`)
   - Run `uv run rpipe verify <lead_path>`.
   - A lead is **never** considered verified on eyeball plots alone. Enforce declared checks: conservation/symmetry invariants, limiting-case benchmarks, convergence order, symbolic-numeric cross-checks, pytest tests, and zero-`sorry` Lean / UNSAT Z3 checks.
   - Iterate autonomously inside Stage 2 <-> Stage 3 until verification passes or reveals a genuine mathematical/physical falsification.

4. **Stage 4 — Evaluation & Synthesis** (`04-lead-evaluation`)
   - Write `evaluation.md` with an honest verdict (`confirmed`, `falsified`, `inconclusive`, or `parked`), update `lead.yaml` status, summarize evidence & failure modes, propose concrete follow-up leads, and decide whether any reusable primitives should be promoted into `src/rpipe/shared/`.
   - Update the parent `projects/<project>/README.md` lead table (or run `uv run rpipe status`).

---

## 3. Non-Negotiable Scientific & Engineering Rules

- **Treat the user as a researcher, not a software developer.** Never ask the researcher to manually debug Python environments, memorize CLI flags, or run boilerplate commands you can run yourself.
  - The user may not even have Python installed yet. If `uv`, Python, `.venv`, or any required math/physics package is missing, proactively heal the setup yourself: run `.\setup.ps1` on Windows (or install `uv` via `curl -LsSf https://astral.sh/uv/install.sh | sh` on macOS/Linux and run `uv sync --extra all --extra dev` — `uv` automatically downloads Python 3.11+), then verify with `uv run rpipe doctor --json`.
  - Run `rpipe` commands, simulations, and verification gates yourself and present results in clear mathematical/physical language (equations, plots, tables, verdicts).
  - If an optional external toolchain (like Lean 4 via `elan` or GPU JAX) is needed, explain plainly what it unlocks and offer either to help install it or use Z3/SymPy/CPU instead.
- **Honest falsification is a win.** Never massage parameters, weaken tolerances, suppress errors, or insert `sorry`/`admit` to make a conjecture look true.
- **No silent hacks.** Never hardcode expected outputs or fudge factors in tests or simulations.
- **Keep outputs LLM-readable.** Every executed script should emit a compact `summary.json` (key scalars, pass/fail flags, artifact paths) using `rpipe.helpers.io.save_summary` rather than dumping raw arrays to stdout.
- **Stay local to the lead.** Keep experimental code inside `projects/<project>/leads/<lead-id>/work/`. Only promote clean, tested, domain-general code to `src/rpipe/shared/`.
- **Use CLI JSON mode when inspecting workspace state:** `uv run rpipe status --json` gives an exact machine-readable overview of all projects and leads without reading dozens of files.

---

## 4. Essential CLI Commands

```bash
.\setup.ps1                                 # Windows one-step zero-Python setup
uv run rpipe doctor [--json]
uv run rpipe status [--project <name>] [--json]
uv run rpipe inspect-ref <path> [--pages 1-5] [--json]
uv run rpipe init-project <project-slug> --title "..." --summary "..."
uv run rpipe new-lead <project-slug> <lead-slug> --title "..." --kind <numerical|symbolic|formal|hybrid|theoretical>
uv run rpipe run <lead-path> -- <command...> [--seed 42] [--timeout 300] [--tag baseline]
uv run rpipe verify <lead-path> [--json]
uv run rpipe set-status <lead-path> <exploring|planned|running|verified|confirmed|falsified|inconclusive|parked>
```
