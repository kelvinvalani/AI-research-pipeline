"""SymPy + Z3/SMT formal verification of global Lyapunov stability & phase-space bounds."""

from __future__ import annotations

import json
import sys

import sympy as sp
import z3

from rpipe.helpers.io import get_run_dir, save_summary


def prove_all() -> dict:
    # 1. SymPy exact Lie derivative dH/dt = 0
    q_s, p_s, w_s, l_s = sp.symbols("q p omega lam", real=True, positive=True)
    H_s = sp.Rational(1, 2) * p_s**2 + sp.Rational(1, 2) * w_s**2 * q_s**2 + sp.Rational(1, 4) * l_s * q_s**4
    dH_dt = sp.simplify(sp.diff(H_s, q_s) * sp.diff(H_s, p_s) - sp.diff(H_s, p_s) * sp.diff(H_s, q_s))
    sympy_lie_zero = dH_dt == 0

    # 2. Z3 real nonlinear arithmetic (NRA) proofs
    q, p, w, lam, e0 = z3.Reals("q p omega lam E0")
    H = z3.Q(1, 2) * p * p + z3.Q(1, 2) * w * w * q * q + z3.Q(1, 4) * lam * q * q * q * q
    assumptions = [w > 0, lam > 0]

    # 2a. Non-vacuity check (assumptions MUST be satisfiable)
    s_vac = z3.Solver()
    s_vac.add(*assumptions, q == 1, p == 0)
    non_vacuous = s_vac.check() == z3.sat

    # 2b. Strict positivity: (q != 0 \/ p != 0) => H(q, p) > 0
    s_pos = z3.Solver()
    s_pos.add(*assumptions, z3.Or(q != 0, p != 0), z3.Not(H > 0))
    strict_positivity_proved = s_pos.check() == z3.unsat

    # 2c. Exact energy-level bounds: H(q, p) <= E0 => (w^2 q^2 <= 2 E0 /\ p^2 <= 2 E0)
    s_bound = z3.Solver()
    s_bound.add(*assumptions, H <= e0, z3.Not(z3.And(w * w * q * q <= 2 * e0, p * p <= 2 * e0)))
    amplitude_bounds_proved = s_bound.check() == z3.unsat

    # 2d. Negative control: when lam < 0, H(q, p) < 0 IS reachable (counterexample exists)
    s_neg = z3.Solver()
    s_neg.add(w == 1, lam == -1, p == 0, H < 0)
    neg_control_sat = s_neg.check() == z3.sat
    counterexample = None
    if neg_control_sat:
        m = s_neg.model()
        counterexample = {
            "omega": str(m[w]),
            "lambda": str(m[lam]),
            "q": str(m[q]),
            "p": str(m[p]),
        }

    all_passed = all(
        [
            sympy_lie_zero,
            non_vacuous,
            strict_positivity_proved,
            amplitude_bounds_proved,
            neg_control_sat,
        ]
    )
    return {
        "sympy_dH_dt_zero": sympy_lie_zero,
        "z3_assumptions_non_vacuous": non_vacuous,
        "z3_strict_positivity_unsat": strict_positivity_proved,
        "z3_amplitude_bounds_unsat": amplitude_bounds_proved,
        "z3_negative_control_counterexample_found": neg_control_sat,
        "negative_control_witness": counterexample,
        "all_passed": all_passed,
    }


def main() -> int:
    result = prove_all()
    save_summary(result, run_dir=get_run_dir())
    print(json.dumps(result, indent=2))
    return 0 if result["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
