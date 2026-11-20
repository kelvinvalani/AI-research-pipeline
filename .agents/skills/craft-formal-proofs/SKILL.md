---
name: craft-formal-proofs
description: >-
  Craft skill for machine-checked mathematical proofs and counterexample search using
  Lean 4 and Z3/SMT: rigorous statement hygiene, zero-sorry/clean-axiom audits,
  non-vacuity checks, and bridging informal math to formal verification.
---

# Craft: Formal Proofs & SMT Verification (Lean 4 & Z3)

Load this skill when proving theorems formally, checking inequalities/invariants with Z3, or searching for counterexamples to a conjecture.

## Choosing Between Z3/SMT and Lean 4

- **Use Z3 (`z3-solver` in Python)** first for:
  - Rapid conjecture stress-testing & counterexample search (real nonlinear arithmetic `NRA`, linear arithmetic, bitvectors, algebraic inequalities, Lyapunov positivity/boundedness).
  - Decidable finite-dimensional algebraic/logical invariants before investing time in a full Lean proof.
- **Use Lean 4 (`.lean` files)** for:
  - Full machine-checked proofs with quantifiers over infinite structures, induction, analysis, algebra, and reusable theorem libraries.

## Z3 / SMT Rigor Rules

1. **Always Prove Non-Vacuity First**
   Before proving `Assumptions => Conclusion` by showing `Assumptions ∧ ¬Conclusion` is `unsat`, **first verify that `Assumptions` alone is `sat`**! Otherwise an inconsistent set of assumptions vacuously "proves" anything.
2. **Distinguish `unsat`, `sat`, and `unknown`**
   - `unsat` (of negated goal, with `sat` assumptions): valid machine-checked proof in Z3's theory.
   - `sat` (of negated goal): genuine counterexample! Extract `solver.model()`, verify it independently in exact rational/SymPy arithmetic, and report it in `summary.json`.
   - `unknown`: solver timed out or hit undecidable nonlinear arithmetic — NEVER treat `unknown` as proved.
3. **Register Z3 Proofs in `verification.checks`** so `rpipe verify` re-runs them deterministically.

## Lean 4 Rigor Rules

1. **Zero Shortcuts Policy**
   `rpipe verify` scans every `.lean` file declared in `lead.yaml` under `verification.lean_files` and **fails immediately** if it finds:
   - `sorry` or `admit`
   - custom `axiom` declarations (unless explicitly audited and documented)
   - `native_decide` or `implemented_by` escapes
2. **Statement Fidelity Audit**
   A formally verified Lean theorem is useless if the Lean statement subtly mis-encodes the mathematical conjecture (e.g., `Nat` subtraction truncating to `0`, missing positivity hypotheses, or vacuous definitions). Always cross-check the Lean type signature line-by-line against `notes/01_background.md` and `lead.yaml`.
3. **Axiom Inspection**
   At the end of key Lean files, include `#print axioms <theorem_name>` (or verify in checks) so you know the proof relies only on standard Lean foundations (`propext`, `Classical.choice`, `Quot.sound`).
4. **Graceful Local Environment Handling**
   If `lean` / `lake` is not installed on the current machine, still keep `.lean` artifacts syntactically clean and tested via Z3/SymPy counterparts where possible, and note in `evaluation.md` that Lean kernel compilation is pending a Lean toolchain. Never claim a `.lean` file is machine-verified unless `lean` actually compiled it with exit code 0.
