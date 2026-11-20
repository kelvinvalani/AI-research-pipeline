"""Multi-layer physics & mathematical verification checks for Lead 001."""

from __future__ import annotations

import json
import sys

import numpy as np
import sympy as sp

from rpipe.helpers.checks import (
    check_analytic_limit,
    check_conservation,
    check_convergence_order,
    check_symbolic_numeric_agreement,
    run_check_suite,
)
from work.simulate import hamiltonian, integrate_rk4, integrate_verlet


def verify_harmonic_limit():
    omega = 1.7
    q0 = 1.2
    dt = 0.005
    n_steps = 1000
    t, q_num, _ = integrate_verlet(q0, 0.0, omega=omega, lam=0.0, dt=dt, n_steps=n_steps)
    q_exact = q0 * np.cos(omega * t)
    return check_analytic_limit(
        q_num, q_exact, rtol=1e-3, atol=1e-4, name="harmonic_analytic_limit"
    )


def verify_verlet_convergence():
    omega, lam, q0, p0 = 1.0, 1.0, 1.0, 0.0
    t_end = 2.0
    # High-resolution reference solution
    _, q_ref, _ = integrate_verlet(q0, p0, omega=omega, lam=lam, dt=0.0005, n_steps=4000)
    dts = [0.08, 0.04, 0.02, 0.01]
    errs = []
    for dt in dts:
        n_steps = int(round(t_end / dt))
        _, q_num, _ = integrate_verlet(q0, p0, omega=omega, lam=lam, dt=dt, n_steps=n_steps)
        errs.append(abs(float(q_num[-1]) - float(q_ref[-1])))
    return check_convergence_order(dts, errs, expected_order=2.0, order_tol=0.15, name="verlet_order")


def verify_rk4_convergence():
    omega, lam, q0, p0 = 1.0, 1.0, 1.0, 0.0
    t_end = 2.0
    _, q_ref, _ = integrate_rk4(q0, p0, omega=omega, lam=lam, dt=0.001, n_steps=2000)
    dts = [0.2, 0.1, 0.05, 0.025]
    errs = []
    for dt in dts:
        n_steps = int(round(t_end / dt))
        assert abs(n_steps * dt - t_end) < 1e-12
        _, q_num, _ = integrate_rk4(q0, p0, omega=omega, lam=lam, dt=dt, n_steps=n_steps)
        errs.append(abs(float(q_num[-1]) - float(q_ref[-1])))
    return check_convergence_order(dts, errs, expected_order=4.0, order_tol=0.2, name="rk4_order")


def verify_verlet_time_reversal_and_conservation():
    omega, lam, q0, p0, dt, n_steps = 1.0, 1.0, 1.5, 0.3, 0.05, 400
    _, q_fwd, p_fwd = integrate_verlet(q0, p0, omega=omega, lam=lam, dt=dt, n_steps=n_steps)
    _, q_rev, p_rev = integrate_verlet(
        float(q_fwd[-1]), -float(p_fwd[-1]), omega=omega, lam=lam, dt=dt, n_steps=n_steps
    )
    rev_check = check_analytic_limit(
        [float(q_rev[-1]), float(-p_rev[-1])],
        [q0, p0],
        rtol=1e-11,
        atol=1e-11,
        name="verlet_time_reversal",
    )
    if not rev_check.passed:
        return rev_check
    energies = hamiltonian(q_fwd, p_fwd, omega, lam)
    return check_conservation(energies, rtol=2e-3, atol=1e-8, name="verlet_bounded_energy")


def verify_symbolic_hamilton_equations():
    q, p, omega, lam = sp.symbols("q p omega lam", real=True)
    H = sp.Rational(1, 2) * p**2 + sp.Rational(1, 2) * omega**2 * q**2 + sp.Rational(1, 4) * lam * q**4
    dq_dt = sp.diff(H, p)
    dp_dt = -sp.diff(H, q)
    dH_dt = sp.simplify(sp.diff(H, q) * dq_dt + sp.diff(H, p) * dp_dt)
    samples = [
        {q: 0.73, p: -1.19, omega: 1.41, lam: 0.87},
        {q: -2.11, p: 0.43, omega: 0.62, lam: 2.35},
        {q: 1.37, p: 1.92, omega: 2.13, lam: 0.31},
    ]
    return check_symbolic_numeric_agreement(
        dH_dt, sp.Integer(0), samples, name="symbolic_dH_dt_zero"
    )


def main() -> int:
    passed, results = run_check_suite(
        [
            verify_harmonic_limit,
            verify_verlet_convergence,
            verify_rk4_convergence,
            verify_verlet_time_reversal_and_conservation,
            verify_symbolic_hamilton_equations,
        ]
    )
    print(json.dumps([r.to_dict() for r in results], indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
