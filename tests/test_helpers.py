"""Tests for scientific verification helpers."""

from __future__ import annotations

import sympy as sp

from rpipe.helpers.checks import (
    check_analytic_limit,
    check_conservation,
    check_convergence_order,
    check_symbolic_numeric_agreement,
    check_symmetry,
)


def test_check_conservation() -> None:
    ok = check_conservation([1.0, 1.0 + 1e-8, 1.0 - 2e-8], rtol=1e-6)
    assert ok.passed is True
    bad = check_conservation([1.0, 1.05, 1.10], rtol=1e-3)
    assert bad.passed is False


def test_check_convergence_order() -> None:
    hs = [0.2, 0.1, 0.05, 0.025]
    errs = [0.5 * (h**2) for h in hs]
    res = check_convergence_order(hs, errs, expected_order=2.0, order_tol=0.05)
    assert res.passed is True
    assert abs(res.metrics["measured_order"] - 2.0) < 1e-3


def test_check_analytic_limit_and_symmetry() -> None:
    import numpy as np

    assert (
        check_analytic_limit(
            np.array([1.0, 2.0]), np.array([1.0 + 1e-7, 2.0 - 1e-7]), rtol=1e-5
        ).passed
        is True
    )
    assert check_symmetry(np.array([1.0, -2.0]), np.array([-1.0, 2.0]), sign=-1.0).passed is True


def test_check_symbolic_numeric_agreement() -> None:
    x = sp.Symbol("x", real=True)
    res = check_symbolic_numeric_agreement(
        sp.sin(x) ** 2 + sp.cos(x) ** 2,
        sp.Integer(1),
        [{x: 0.37}, {x: 1.91}, {x: -2.43}],
    )
    assert res.passed is True
