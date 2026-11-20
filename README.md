# AI Research Pipeline (Theoretical Mathematics & Physics)

A lean, single-researcher, agent-native repository for turning high-level theoretical math and physics ideas into structured research notes, computational/proof artifacts, verified runs, and honest evaluations — designed to scale cleanly across dozens of projects and leads.

## Quickstart

```bash
# Install core CLI + numerics/symbolic/formal/dev extras
uv sync --extra all --extra dev

# Inspect all projects and leads
uv run rpipe status

# Start a new research project and a lead
uv run rpipe init-project nonlinear-waves --title "Nonlinear Wave Blowup" --summary "Investigating self-similar blowup profiles."
uv run rpipe new-lead nonlinear-waves 001-self-similar-ansatz --title "Self-similar ODE profile" --kind hybrid

# Execute a script inside a lead with provenance capture (manifest.json + summary.json + ledger)
uv run rpipe run projects/example-anharmonic-oscillator/leads/001-symplectic-vs-rk4-energy-drift -- python work/simulate.py

# Run all declared scientific verification checks + tests for a lead
uv run rpipe verify projects/example-anharmonic-oscillator/leads/001-symplectic-vs-rk4-energy-drift

# Run core framework tests
uv run pytest
```

## How It Works

1. **Projects -> Leads Hierarchy**: Each broad topic lives in `projects/<project>/`. Every hypothesis, ansatz, proof attempt, or numerical experiment is an isolated lead in `projects/<project>/leads/<lead-id>/` with 5 clear zones:
   - `lead.yaml` — hypothesis, math formulation, assumptions, falsification criteria, verification checks, status.
   - `notes/` — background research, literature notes, hand/LaTeX derivations.
   - `work/` — flexible computational/proof artifacts (Python, SymPy, Lean 4, Z3, notebooks, data scripts). No forced OOP base classes.
   - `runs/` — immutable run directories (`manifest.json`, `summary.json`, logs, figures) + append-only `ledger.jsonl`.
   - `evaluation.md` — structured final verdict (`confirmed` / `falsified` / `inconclusive` / `parked`), evidence, failure modes, and proposed next leads.
2. **Modular Agent Skills (`.agents/skills/`)**: Stage playbooks (`01-idea-to-spec`, `02-lead-execution`, `03-scientific-verification`, `04-lead-evaluation`) and craft playbooks (`craft-numerical-simulation`, `craft-symbolic-math`, `craft-formal-proofs`, `craft-research-and-derivations`) guide any coding LLM through disciplined research.
3. **Thin Python Micro-SDK (`src/rpipe/`)**:
   - `rpipe` CLI for scaffolding, provenance-tracked execution, multi-layer verification, and workspace status.
   - `rpipe.helpers.checks` for conservation laws, convergence order, symmetries, analytic limits, and symbolic-numeric cross-checks.
   - `rpipe.helpers.io` for LLM-readable `summary.json` and structured telemetry.
   - `rpipe.shared` for promoting reusable math/physics primitives out of verified leads.

## Optional Lean 4 Support

Lean 4 verification (`rpipe verify` checking `.lean` files for compilation errors, `sorry`, `admit`, and non-standard axioms) works automatically whenever `lean` / `lake` is installed on `PATH`, and degrades gracefully with a clear diagnostic if Lean is not installed locally.
