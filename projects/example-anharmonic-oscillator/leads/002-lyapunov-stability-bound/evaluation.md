# Lead Evaluation — Global Lyapunov Positivity & Phase-Space Bounds

- **Lead ID**: `002-lyapunov-stability-bound`
- **Project**: `example-anharmonic-oscillator`
- **Final Verdict**: `CONFIRMED`
- **Verification Gate**: `PASS` (`runs/latest_verification.json`; Lean kernel compilation skipped locally since `lean` is not installed)
- **Key Run(s)**: `runs/20261120T143945Z_proof`

---

## 1. Executive Summary

We formally verified that the quartic oscillator Hamiltonian $H(q, p) = \frac{1}{2}p^2 + \frac{1}{2}\omega^2 q^2 + \frac{1}{4}\lambda q^4$ is strictly positive away from $(0,0)$, conserved along trajectories ($\dot{H} = 0$), and enforces global phase-space bounds $\omega^2 q^2 \le 2E_0$ and $p^2 \le 2E_0$ for all $\omega > 0, \lambda > 0$. **Confirmed** via SymPy + Z3 real nonlinear arithmetic (`unsat` negated goals with non-vacuity verified and $\lambda < 0$ counterexample confirmed).

## 2. Evaluation Against Criteria

| Criterion (`lead.yaml`) | Evidence / Metric / Proof | Status |
| :--- | :--- | :--- |
| Z3 non-vacuity (`sat`) + strict positivity & amplitude bounds (`unsat`) | `z3_assumptions_non_vacuous: true`, `z3_strict_positivity_unsat: true`, `z3_amplitude_bounds_unsat: true` (`runs/20261120T143945Z_proof/summary.json`) | **MET** |
| Z3 negative control finds counterexample when $\lambda < 0$ | Witness found: `omega = 1, lambda = -1, q = -2, p = 0`, where $H(-2, 0) = -2 < 0$ | **MET** |
| SymPy exact $\dot{H} = 0$ | `sympy_dH_dt_zero: true` | **MET** |
| Lean 4 `work/Stability.lean` passes zero-sorry / clean-axiom audit | `lean-audit:Stability.lean` PASSED (`No sorry/admit/axiom/native_decide escapes found.`) | **MET** (kernel compile pending local `lean`) |

## 3. Key Results

- Proved over all real $(q, p, \omega, \lambda, E_0) \in \mathbb{R}^5$ with $\omega > 0, \lambda > 0$ in Z3 NRA:
  - $(q, p) \neq (0, 0) \implies H(q, p) > 0$
  - $H(q, p) \le E_0 \implies \omega^2 q^2 \le 2E_0 \land p^2 \le 2E_0$
- Negative control confirms sharpness of $\lambda > 0$: for $\omega = 1, \lambda = -1$, $(q, p) = (-2, 0)$ yields $H = -2 < 0$.
- Lean 4 artifact: `work/Stability.lean` (integer-scaled core Lean 4 proof with `#print axioms` audit, zero Mathlib dependency).

## 4. Verification Audit

- **Non-vacuity check**: Z3 confirmed assumptions ($\omega > 0, \lambda > 0$) are `sat` before proving negated goals `unsat`.
- **Negative control**: Verified explicit falsification witness when $\lambda < 0$, ruling out tautological/vacuous SMT encoding.
- **Lean 4 caveat**: `lean-audit:Stability.lean` passed statically, while `lean-compile:Stability.lean` was `skipped` because `lean` is not installed on this workstation. Run `uv run rpipe verify example-anharmonic-oscillator/002-lyapunov-stability-bound --require-lean` once `elan`/Lean 4 is installed to complete kernel compilation.

## 5. Next Leads & Promotion Decisions

- **Proposed Follow-Up Leads**:
  1. `003-damped-duffing-la-salle` (`hybrid`): add linear damping $-\gamma p$ ($\gamma > 0$) and verify asymptotic stability via LaSalle's invariance principle + numerical decay rate matching.
- **Promote to `src/rpipe/shared/`?**: No — proof scripts are problem-specific; the generic `audit_lean_source` and `verify_lead` utilities already live in `src/rpipe/verify.py`.
