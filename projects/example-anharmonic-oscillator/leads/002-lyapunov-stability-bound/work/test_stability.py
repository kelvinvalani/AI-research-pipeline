"""Unit tests for Lead 002 formal stability proofs."""

from __future__ import annotations

from work.prove_stability import prove_all


def test_formal_stability_proofs_and_negative_control() -> None:
    result = prove_all()
    assert result["sympy_dH_dt_zero"] is True
    assert result["z3_assumptions_non_vacuous"] is True
    assert result["z3_strict_positivity_unsat"] is True
    assert result["z3_amplitude_bounds_unsat"] is True
    assert result["z3_negative_control_counterexample_found"] is True
    assert result["all_passed"] is True
