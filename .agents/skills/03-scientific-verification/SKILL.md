---
name: 03-scientific-verification
description: >-
  Stage 3 of the research pipeline: enforce multi-layer mathematical and physical
  verification (invariants, symmetries, limiting cases, convergence, symbolic-numeric
  cross-checks, pytest, Z3/Lean checks) before trusting any simulation or proof result.
---

# Stage 3: Scientific Verification Gate

Use this skill after producing artifacts in Stage 2 and **always before** declaring a lead confirmed or writing a final `evaluation.md`.

## Objective

Catch subtle math, physics, discretization, sign, factor-of-$2\pi$, and formal-proof bugs automatically. A lead only passes Stage 3 when its declared scientific checks pass via `uv run rpipe verify <lead-path>`.

## The Multi-Layer Verification Checklist

Apply every layer relevant to the lead's `kind` and declare them in `lead.yaml` under `verification:`:

### Layer 1 — Software & Structural Integrity
- `pytest` unit tests in `work/test_*.py` testing helper functions, edge cases, input shapes, and error handling.
- Deterministic replay: running twice with the same `RPIPE_SEED` reproduces identical numbers.

### Layer 2 — Physical & Mathematical Invariants (for `numerical` / `hybrid`)
Use `rpipe.helpers.checks` where helpful:
- **Conservation laws** (`check_conservation`): energy, momentum, angular momentum, probability norm $\int |\psi|^2 dx = 1$, symplectic form, divergence-free constraints.
- **Symmetries** (`check_symmetry`): time-reversal, parity, gauge/rotation invariance, permutation symmetry.
- **Analytic & limiting cases** (`check_analytic_limit`): recover exact closed-form solutions when nonlinearity $\to 0$, coupling $\to 0$, or in 1D/free-particle limits.
- **Convergence order** (`check_convergence_order`): refine $\Delta t$ or $\Delta x$ across at least 3 resolutions and verify the measured empirical order $p$ matches the theoretical order of the scheme.
- **Dimensional consistency**: verify equations in dimensionless form or check scaling laws under rescaling of units.

### Layer 3 — Symbolic Cross-Verification (for `symbolic` / `hybrid`)
- **Independent numerical spot-checks** (`check_symbolic_numeric_agreement`): evaluate closed-form symbolic identities, derivatives, or integrals at multiple random non-special parameter points (avoiding $0, 1, \pi$ coincidences) against high-precision numerical evaluation.
- **Round-trip checks**: differentiate an indefinite integral to recover the integrand; substitute an ODE/PDE solution back into the differential operator and confirm residual $= 0$.

### Layer 4 — Formal Proof Integrity (for `formal` / `hybrid`)
- **Lean 4**: list `.lean` files under `verification.lean_files` in `lead.yaml`. `rpipe verify` compiles them (when `lean` is installed) and **statically rejects** any `sorry`, `admit`, `axiom` declarations, or `native_decide` shortcuts.
- **Z3 / SMT**: confirm the negated conjecture is strictly `unsat` (not `unknown`), verify model sanity on a satisfiable witness (to prove constraints aren't vacuously inconsistent!), and test boundary cases.

## Running the Gate

```bash
uv run rpipe verify projects/<project>/leads/<lead-id> --json
```

### Handling Failures
- **Implementation bug** (wrong sign, unstable step size, missing boundary term, broken Lean tactic): return to Stage 2, fix the artifact, and re-verify.
- **Genuine mathematical/physical falsification** (the code & invariants are verified correct, yet the conjecture fails or Z3 yields a valid counterexample): **do NOT weaken the check!** Mark the verification of the *instrument* as passing, record the counterexample/violation clearly, and proceed to Stage 4 to record an honest `falsified` verdict.

Once all declared verification checks pass, mark the lead:
```bash
uv run rpipe set-status projects/<project>/leads/<lead-id> verified
```
