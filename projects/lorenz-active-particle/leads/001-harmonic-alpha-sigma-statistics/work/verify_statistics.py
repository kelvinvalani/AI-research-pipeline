"""Registered Stage 3 gate, including audits of provenance-captured long runs."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import sympy as sp

from rpipe.helpers.checks import (
    CheckResult,
    check_analytic_limit,
    check_symbolic_numeric_agreement,
    check_symmetry,
    run_check_suite,
)
from rpipe.helpers.io import get_seed, save_summary
from work.harmonic_particle import normalized_filter, rtp_first_passage_rate, rtp_moments_y
from work.lorenz_signal import SignalConfig, lorenz_rhs, simulate_lorenz
from work.stationary_statistics import compute_stationary_statistics


EVIDENCE_RUNS = {
    "refinement": "20261125T093355Z",
    "decisive": "20261125T093718Z",
    "tail": "20261125T094642Z",
}


def _load_evidence(name: str) -> dict:
    path = Path("runs") / EVIDENCE_RUNS[name] / "summary.json"
    return json.loads(path.read_text(encoding="utf-8"))


def symbolic_rtp_moment_check() -> CheckResult:
    a = sp.symbols("a", real=True, positive=True)
    beta_second = sp.beta(sp.Rational(3, 2), a) / sp.beta(sp.Rational(1, 2), a)
    beta_fourth = sp.beta(sp.Rational(5, 2), a) / sp.beta(sp.Rational(1, 2), a)
    samples = [{a: value} for value in (0.17, 0.43, 0.91, 1.7, 4.2, 11.3)]
    second = check_symbolic_numeric_agreement(
        beta_second, 1 / (2 * a + 1), samples, rtol=1.0e-12, name="rtp_second_moment"
    )
    fourth = check_symbolic_numeric_agreement(
        beta_fourth,
        3 / ((2 * a + 1) * (2 * a + 3)),
        samples,
        rtol=1.0e-12,
        name="rtp_fourth_moment",
    )
    return CheckResult(
        name="rtp_moments_symbolic_numeric",
        passed=second.passed and fourth.passed,
        message=(
            f"second max relerr={second.metrics['max_rel_err']:.3e}; "
            f"fourth max relerr={fourth.metrics['max_rel_err']:.3e}"
        ),
        metrics={"second": second.to_dict(), "fourth": fourth.to_dict()},
    )


def lorenz_symmetry_check() -> CheckResult:
    samples = np.asarray(((1.3, -2.1, 17.0), (-8.2, 3.4, 24.0), (5.0, 7.0, 31.0)))
    original = np.asarray([lorenz_rhs(0.0, state, 10.0) for state in samples])
    transformed_states = samples.copy()
    transformed_states[:, :2] *= -1.0
    transformed_rhs = np.asarray([lorenz_rhs(0.0, state, 10.0) for state in transformed_states])
    expected = original.copy()
    expected[:, :2] *= -1.0
    return check_symmetry(
        expected.ravel(), transformed_rhs.ravel(), rtol=1.0e-13, atol=1.0e-13,
        name="lorenz_xy_inversion"
    )


def exact_filter_check() -> CheckResult:
    mu, dt, y0 = 0.73, 0.013, -0.27
    sign = np.ones(801, dtype=np.int8)
    numerical = normalized_filter(sign, mu, dt, y0)
    time = np.arange(sign.size) * dt
    analytic = 1.0 + (y0 - 1.0) * np.exp(-mu * time)
    return check_analytic_limit(
        numerical, analytic, rtol=2.0e-13, atol=2.0e-13,
        name="constant_sign_exact_filter"
    )


def support_check() -> CheckResult:
    rng = np.random.default_rng(get_seed())
    sign = rng.choice(np.asarray((-1, 1), dtype=np.int8), size=20000)
    values = normalized_filter(sign, 0.1, 0.01, 0.5)
    excess = float(max(0.0, np.max(np.abs(values)) - 1.0))
    return CheckResult(
        name="forward_invariant_support",
        passed=excess <= 5.0e-14,
        message=f"maximum normalized support excess={excess:.3e}",
        metrics={"support_excess": excess},
    )


def first_passage_identity_check() -> CheckResult:
    small = rtp_first_passage_rate(1.0, 0.02)
    large = rtp_first_passage_rate(1.0, 200.0)
    small_error = abs(small - 0.02) / 0.02 if small is not None else np.inf
    large_error = abs(large - 1.0) if large is not None else np.inf
    passed = small is not None and large is not None and small_error < 0.12 and large_error < 0.06
    return CheckResult(
        name="rtp_first_passage_root_and_limits",
        passed=passed,
        message=f"small-gamma relerr={small_error:.3e}, large-gamma abserr={large_error:.3e}",
        metrics={"theta_small": small, "theta_large": large},
    )


def deterministic_replay_check() -> CheckResult:
    config = SignalConfig(10.0, burn_in=20.0, duration=30.0, future_horizon=0.0, dt=0.01)
    first = simulate_lorenz(config)
    second = simulate_lorenz(config)
    state_error = float(np.max(np.abs(first.states - second.states)))
    crossing_error = float(np.max(np.abs(first.crossing_times - second.crossing_times)))
    passed = np.array_equal(first.states, second.states) and np.array_equal(
        first.crossing_times, second.crossing_times
    )
    return CheckResult(
        name="deterministic_replay",
        passed=passed,
        message=f"state max error={state_error:.3e}; crossing max error={crossing_error:.3e}",
        metrics={"state_max_error": state_error, "crossing_max_error": crossing_error},
    )


def ode_tolerance_check() -> CheckResult:
    rows = []
    for rtol, atol in ((2.0e-10, 2.0e-12), (2.0e-11, 2.0e-13)):
        signal = simulate_lorenz(
            SignalConfig(
                float(np.sqrt(50.0)), burn_in=0.0, duration=20.0,
                future_horizon=0.0, dt=0.005, rtol=rtol, atol=atol
            )
        )
        rows.append(signal.crossing_times)
    count = min(row.size for row in rows)
    relative = float(
        np.max(np.abs(rows[0][:count] - rows[1][:count]))
        / max(float(np.max(np.abs(rows[1][:count]))), 1.0e-15)
    )
    return CheckResult(
        name="ode_tolerance_crossing_times",
        passed=count > 3 and relative < 0.02,
        message=f"{count} common crossings; max relative time change={relative:.3e}",
        metrics={"common_crossings": count, "max_relative_change": relative},
    )


def fixed_realization_timestep_check() -> CheckResult:
    signal = simulate_lorenz(
        SignalConfig(10.0, burn_in=100.0, duration=600.0, future_horizon=0.0, dt=0.005)
    )
    gamma = signal.summary()["gamma_eff"]
    changes = {}
    for alpha in (0.05, 0.25, 1.0, 5.0):
        coarse = compute_stationary_statistics(
            signal.sign[::2], 0.01, alpha, gamma, analysis_duration=600.0
        ).record["second_moment_y"]
        fine = compute_stationary_statistics(
            signal.sign, 0.005, alpha, gamma, analysis_duration=600.0
        ).record["second_moment_y"]
        changes[str(alpha)] = float(abs(coarse - fine) / max(abs(fine), 1.0e-15))
    maximum = max(changes.values())
    return CheckResult(
        name="fixed_realization_timestep_refinement",
        passed=maximum < 0.02,
        message=f"maximum second-moment change={maximum:.3%}",
        metrics={"relative_changes": changes},
    )


def long_run_refinement_audit() -> CheckResult:
    refinement = _load_evidence("refinement")
    decisive = _load_evidence("decisive")
    stationary = decisive["stationary"]
    falsified = [row["alpha"] for row in stationary if row["collapse_falsified"]]
    unresolved = [row["alpha"] for row in stationary if not row["numerically_converged"]]
    passed = (
        refinement["gates"]["timestep_two_percent_pass"]
        and decisive["gates"]["rate_two_percent_pass"]
        and falsified == [0.25, 0.5, 1.0]
        and unresolved == [0.05, 0.1]
    )
    return CheckResult(
        name="long_run_refinement_and_stationary_falsification",
        passed=passed,
        message=f"verified collapse failures at alpha={falsified}; unresolved alpha={unresolved}",
        metrics={"falsified_alphas": falsified, "unresolved_alphas": unresolved},
    )


def exponent_and_tail_audit() -> CheckResult:
    decisive = _load_evidence("decisive")
    tail = _load_evidence("tail")
    changes = decisive["exponent_relative_changes_5120_to_10240"]
    tail_spread = tail["threshold_rate_relative_spread"]
    passed = (
        decisive["gates"]["all_exponents_five_percent_pass"]
        and tail["gates"]["five_percent_ensemble_convergence"]
        and tail_spread >= 0.10
    )
    return CheckResult(
        name="relaxation_convergence_and_tail_model_classification",
        passed=passed,
        message=(
            "relaxation/FPT numerical exponents converge within 5%; "
            f"first-passage exponential rejected (threshold-rate spread={tail_spread:.1%})"
        ),
        metrics={"exponent_relative_changes": changes, "tail_rate_spread": tail_spread},
    )


def sweep_completeness_check() -> CheckResult:
    decisive = _load_evidence("decisive")
    unstable = decisive["gates"]["unstable_modality_points"]
    return CheckResult(
        name="full_sweep_density_modality_and_convergence",
        passed=False,
        message=(
            "unresolved: long-record refinement covers sigma=sqrt(50) only; "
            f"modality remains estimator-sensitive at alpha={unstable}, and other reversing sigma points are unrefined"
        ),
        metrics={
            "refined_sigma": [float(np.sqrt(50.0))],
            "unrefined_reversing_sigma": [10.0, 11.530715390799683, 14.724544808607865],
            "unstable_modality_alphas": unstable,
        },
    )


def main() -> None:
    all_passed, checks = run_check_suite(
        (
            symbolic_rtp_moment_check,
            lorenz_symmetry_check,
            exact_filter_check,
            support_check,
            first_passage_identity_check,
            deterministic_replay_check,
            ode_tolerance_check,
            fixed_realization_timestep_check,
            long_run_refinement_audit,
            exponent_and_tail_audit,
            sweep_completeness_check,
        )
    )
    save_summary(
        {
            "stage": 3,
            "status": "genuine_falsification_with_unresolved_sweep",
            "all_declared_checks_passed": all_passed,
            "checks": [check.to_dict() for check in checks],
            "evidence_runs": EVIDENCE_RUNS,
            "rtp_reference_moments_mu1_gamma1": rtp_moments_y(1.0, 1.0),
        }
    )
    if not all_passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
