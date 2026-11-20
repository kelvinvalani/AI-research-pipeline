# AI Research Pipeline (Theoretical Mathematics & Physics)

A lean, single-researcher, agent-native repository for turning high-level theoretical math and physics ideas into structured research notes, computational/proof artifacts, verified runs, and honest evaluations — designed to scale cleanly across dozens of projects and leads.

## Start Here (No Coding or Pre-Installed Python Required)

You do **not** need to be a software developer — or even have Python installed yet — to use this repository:

1. **One-time setup** (automatically installs `uv`, downloads Python 3.11+, and installs all math/physics libraries):
   - **Easiest (any OS)**: Open this folder in your AI IDE (Antigravity, Cursor, Codex, etc.) and simply type in chat: *"Set up my environment."*
   - **Windows (one-step script)**: Run:
     ```powershell
     powershell -ExecutionPolicy Bypass -File .\setup.ps1
     ```
   - **macOS / Linux (one-liner)**:
     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh && uv sync --extra all --extra dev && uv run rpipe doctor
     ```
2. **Share your idea (and any papers)**: Drop any PDFs, `.tex` drafts, whiteboard photos, or notebooks into `inbox/` (optional), then describe your math or physics idea in plain English in chat.
3. **Collaborate with the agent**:
   - The agent reads your references and asks focused clarifying questions one at a time (each with a recommended default).
   - It writes out the formal mathematical spec & falsification criteria and **pauses for your approval** before coding.
   - Once you approve, it runs simulations/derivations/proofs, enforces scientific verification checks, and delivers an honest `evaluation.md` verdict with plots, equations, and suggested next leads.

---

## CLI Quick Reference (Mostly Run by the Agent)

```bash
# One-step Windows setup (zero Python required — installs uv, Python 3.11+, all libraries, runs doctor)
powershell -ExecutionPolicy Bypass -File .\setup.ps1

# Check environment health
uv run rpipe doctor

# Inspect inbox files, projects, and leads
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

1. **Inbox -> Projects -> Leads Hierarchy**:
   - **`inbox/`**: Root drop-in folder for PDFs, `.tex` drafts, whiteboard photos, notebooks, or data files before a project even exists. Mention them in chat and the agent reads them, creates/finds the project, and files them into `projects/<project>/refs/`.
   - **`projects/<project>/`**: Holds `project.yaml`, `README.md`, shared `refs/`, and isolated leads in `leads/<lead-id>/`, each with 5 clear zones:
     - `lead.yaml` — hypothesis, math formulation, assumptions, falsification criteria, verification checks, status.
     - `notes/` — background research, reference digests, hand/LaTeX derivations.
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
