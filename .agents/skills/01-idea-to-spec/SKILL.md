---
name: 01-idea-to-spec
description: >-
  Stage 1 of the research pipeline: inspect workspace & dropped references, grill the
  researcher one question at a time to resolve all math/physics ambiguities, and turn a
  raw idea into a scoped lead with background notes, explicit assumptions, falsification
  criteria, and a verification plan before writing heavy code.
---

# Stage 1: Idea -> Clarify -> Research -> Formal Spec

Use this skill whenever the researcher introduces a new idea, conjecture, ansatz, calculation, or follow-up question.

## Objective

Transform an informal idea into a self-contained, testable research lead under `projects/<project>/leads/<lead-id>/` with zero ambiguity about what counts as confirmation vs. falsification.

## Procedure

### 1. Check Workspace Context & `inbox/` First
Run:
```bash
uv run rpipe status --json
```
Check whether:
- Any reference files (PDFs, `.tex`, `.bib`, whiteboard images, notebooks, data) are waiting in `inbox/` (`inbox_files` in the JSON output) or mentioned by the researcher from `projects/<project>/refs/` or another path.
- A relevant project already exists under `projects/`, or a new project should be created via `uv run rpipe init-project <slug> --title "..." --summary "..."`.
- A prior lead already tested a closely related or falsified version of this idea. Read any relevant `evaluation.md` files so we do not repeat dead ends.

### 2. Inspect & File Reference Materials
If the researcher dropped files into `inbox/` or referenced existing papers/files:
- **Inspect carefully**:
  - Read `.tex`, `.md`, `.bib`, `.py`, `.csv` directly.
  - For `.pdf` files, use native multimodal reading when available (especially for heavy equations/figures), OR run `uv run rpipe inspect-ref <path> --pages 1-5` (fetching specific target pages so context stays tight).
  - For `.ipynb` notebooks, run `uv run rpipe inspect-ref <path>` (strips binary image blobs cleanly).
  - For whiteboard photos / diagrams (`.png`, `.jpg`), inspect visually with your multimodal file viewer.
- **File out of `inbox/` once the project exists**:
  - Move project-relevant reference files from `inbox/<file>` -> `projects/<project>/refs/<file>` so `inbox/` stays clean and all leads in the project can share the same paper without duplication. (If an attachment is strictly a one-off sketch for a single lead, place it in `projects/<project>/leads/<lead-id>/notes/`.)
  - Record every referenced file in `lead.yaml` under `links.references` with relative path + exact section/page/equation anchors (e.g. `../../refs/paper.pdf (Sec. 3, Eq. 14)`).

### 3. Grill the Researcher Until Zero Critical Ambiguities Remain
Do **not** silently guess missing mathematical, physical, or methodological choices. Before scaffolding or drafting the formal spec, interview the researcher systematically to resolve every open branch of the problem:

- **Rules of the interview**:
  1. **Read first, ask second**: Never ask anything already answered by existing leads, `projects/<project>/`, or dropped files in `inbox/` / `refs/`.
  2. **One question at a time**: Walk through dependencies in logical order (high-level formulation & regime first, then discretization/proof strategy, then success/falsification thresholds).
  3. **Always give a recommended answer**: Propose the strongest mathematically/physically sensible default first so the researcher can confirm in one click or override immediately. Use the IDE's interactive question tool (e.g. `ask_question`) when available, or crisp labeled choices otherwise.
  4. **Know when to stop**: Stop asking as soon as there is a shared, unambiguous specification (do not pad with trivial or redundant questions). Skip the interview only if the researcher explicitly asked you to make reasonable assumptions and run end-to-end.
- **Typical ambiguity checklist for math & physics leads**:
  - Exact mathematical object, dimension $d$, domain, and boundary/initial conditions.
  - Conventions & units (metric signature, $\hbar = c = 1$, nondimensionalization, Fourier conventions).
  - Target parameter regime or asymptotic limit (e.g. weak coupling vs. non-perturbative, finite $N$ vs. large $N$).
  - Desired modality & rigor bar (`numerical` simulation/sweep, `symbolic` derivation, `formal` Z3/Lean proof, `hybrid`, or `theoretical` notes).
  - Concrete **falsification criterion** (what numerical threshold, scaling violation, or counterexample would rule the idea out?).
  - Compute/time scope (quick prototype check vs. full parameter sweep) and whether this extends an existing project or starts a new one.

### 4. Scaffold the Lead
Create a numbered or descriptive lead directory:
```bash
uv run rpipe new-lead <project> <lead-slug> --title "..." --kind <numerical|symbolic|formal|hybrid|theoretical>
```
Choose `kind` deliberately:
- `numerical`: PDE/ODE solvers, Monte Carlo, exact diagonalization, parameter sweeps, numerical optimization.
- `symbolic`: SymPy algebra, perturbative expansions, tensor/differential geometry calculations, analytic limits.
- `formal`: Lean 4 theorem proving or Z3/SMT verification / counterexample search.
- `hybrid`: Combines two or more of the above (very common in theoretical physics & math).
- `theoretical`: Pure derivation, literature synthesis, or conceptual analysis without heavy compute.

### 5. Conduct Background Research & Mathematical Formulation
Load `craft-research-and-derivations` if the idea needs literature context or multi-step hand derivations.
Populate `notes/01_background.md` with:
- **Reference digest** (when working from papers/files in `refs/`): exact conventions, definitions, equation numbers, and assumptions extracted from the source so future turns never have to re-parse a 40-page PDF.
- **Exact notation and conventions** (metric signature, $\hbar, c, k_B$ units, Fourier transform factors, inner product convention, function spaces).
- **Governing equations / theorem statement** before writing a single line of solver code.
- **Known analytic limiting cases** (e.g., $\lambda \to 0$, $N \to \infty$, harmonic limit, low-dimensional case) that will serve as non-negotiable benchmarks in Stage 3.
- **Potential failure modes** (stiffness, singular perturbations, boundary layer, non-convexity, hidden measurability/smoothness hypotheses).

### 6. Fill `lead.yaml` Completely
Every field in `lead.yaml` must be concrete:
- `idea`: 2–4 sentences capturing the researcher's intent.
- `mathematical_formulation`: Exact equations/conjecture statement.
- `assumptions`: Explicit list (never leave domain, regularity, boundary conditions, or parameter regimes implicit).
- `success_criteria`: Measurable quantitative thresholds or formal proof goals.
- `falsification_criteria`: Equally concrete conditions that disprove or invalidate the lead. **If an idea cannot be falsified, refine it until it can be.**
- `artifacts_planned`: Exact files to create in `work/` (e.g., `work/simulate.py`, `work/derive.py`, `work/Proof.lean`, `work/test_*.py`).
- `verification`: Declare `pytest: true`, any `lean_files`, and explicit `checks` commands (invariants, convergence, symbolic-numeric cross-checks).

Update status to `planned`:
```bash
uv run rpipe set-status projects/<project>/leads/<lead-id> planned
```

### 7. Default Human Checkpoint (Spec Approval)
Unless the researcher explicitly asked for an uninterrupted end-to-end run:
1. Present a concise summary of:
   - The mathematical formulation & key assumptions,
   - The planned computational/proof artifact(s),
   - The success vs. falsification criteria and verification checks.
2. Ask the researcher to confirm or adjust before moving to Stage 2 (`02-lead-execution`).

## Anti-Patterns to Avoid
- Silently guessing missing assumptions, boundary conditions, or conventions instead of asking the researcher during Step 3.
- Asking a wall of 10 questions at once instead of resolving dependencies one question at a time with recommended defaults.
- Jumping straight into coding a simulation before writing down conventions, dimensionless parameters, and limiting cases.
- Writing vague success criteria like "plot looks reasonable" or "solution behaves nicely."
- Inventing paper citations or theorem names from memory — always mark unverified references as `[needs citation check]` or verify via web/literature tools.
