---
name: 01-idea-to-spec
description: >-
  Stage 1 of the research pipeline: turn a raw theoretical math or physics idea into a
  scoped, mathematically precise lead with background notes, explicit assumptions,
  falsification criteria, and a verification plan before writing heavy code.
---

# Stage 1: Idea -> Research -> Formal Spec

Use this skill whenever the researcher introduces a new idea, conjecture, ansatz, calculation, or follow-up question.

## Objective

Transform an informal idea into a self-contained, testable research lead under `projects/<project>/leads/<lead-id>/` with zero ambiguity about what counts as confirmation vs. falsification.

## Procedure

### 1. Check Workspace Context First
Run:
```bash
uv run rpipe status --json
```
Check whether:
- A relevant project already exists under `projects/`, or a new project should be created via `uv run rpipe init-project <slug> --title "..." --summary "..."`.
- A prior lead already tested a closely related or falsified version of this idea. Read any relevant `evaluation.md` files so we do not repeat dead ends.

### 2. Scaffold the Lead
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

### 3. Conduct Background Research & Mathematical Formulation
Load `craft-research-and-derivations` if the idea needs literature context or multi-step hand derivations.
Populate `notes/01_background.md` with:
- **Exact notation and conventions** (metric signature, $\hbar, c, k_B$ units, Fourier transform factors, inner product convention, function spaces).
- **Governing equations / theorem statement** before writing a single line of solver code.
- **Known analytic limiting cases** (e.g., $\lambda \to 0$, $N \to \infty$, harmonic limit, low-dimensional case) that will serve as non-negotiable benchmarks in Stage 3.
- **Potential failure modes** (stiffness, singular perturbations, boundary layer, non-convexity, hidden measurability/smoothness hypotheses).

### 4. Fill `lead.yaml` Completely
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

### 5. Default Human Checkpoint (Spec Approval)
Unless the researcher explicitly asked for an uninterrupted end-to-end run:
1. Present a concise summary of:
   - The mathematical formulation & key assumptions,
   - The planned computational/proof artifact(s),
   - The success vs. falsification criteria and verification checks.
2. Ask the researcher to confirm or adjust before moving to Stage 2 (`02-lead-execution`).

## Anti-Patterns to Avoid
- Jumping straight into coding a simulation before writing down conventions, dimensionless parameters, and limiting cases.
- Writing vague success criteria like "plot looks reasonable" or "solution behaves nicely."
- Inventing paper citations or theorem names from memory — always mark unverified references as `[needs citation check]` or verify via web/literature tools.
