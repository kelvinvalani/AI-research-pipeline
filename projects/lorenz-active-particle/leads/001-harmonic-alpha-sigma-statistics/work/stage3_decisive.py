"""Decisive long-record, estimator, and exponent checks for Stage 3."""

from __future__ import annotations

import numpy as np
from scipy.stats import gaussian_kde

from rpipe.helpers.io import get_seed, save_summary
from work.first_passage_statistics import compute_first_passage_statistics
from work.harmonic_particle import fit_exponential_rate, normalized_filter
from work.lorenz_signal import SignalConfig, simulate_lorenz
from work.relaxation_statistics import compute_relaxation_statistics
from work.stationary_statistics import compute_stationary_statistics


SIGMA = float(np.sqrt(50.0))
ALPHAS = (0.05, 0.1, 0.25, 0.5, 1.0, 5.0)


def _relative_change(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return float(abs(a - b) / max(abs(b), 1.0e-15))


def _gamma(crossings: np.ndarray, stop: float) -> float:
    selected = crossings[crossings <= stop]
    return float(1.0 / np.mean(np.diff(selected)))


def _shape_label(score: float) -> str:
    if score > 0.025:
        return "edge_peaked"
    if score < -0.025:
        return "center_peaked"
    return "flat_or_transition"


def _shape_score(grid: np.ndarray, density: np.ndarray) -> float:
    center = int(np.argmin(abs(grid)))
    left = int(np.argmin(abs(grid + 0.2)))
    right = int(np.argmin(abs(grid - 0.2)))
    shoulder = 0.5 * (density[left] + density[right])
    return float((shoulder - density[center]) / max(density[center], 1.0e-15))


def _estimator_diagnostics(sample: np.ndarray) -> list[dict]:
    data = np.concatenate((sample, -sample))
    data = data[:: max(1, data.size // 30000)]
    grid = np.linspace(-0.995, 0.995, 401)
    rows = []
    base = gaussian_kde(data)
    for multiplier in (0.7, 1.0, 1.4):
        kde = gaussian_kde(data)
        kde.set_bandwidth(base.factor * multiplier)
        density = kde(grid)
        density /= np.trapezoid(density, grid)
        score = _shape_score(grid, density)
        rows.append(
            {
                "estimator": f"kde_bandwidth_{multiplier:g}",
                "shape_score": score,
                "modality": _shape_label(score),
            }
        )
    for bins in (80, 120, 160):
        density, edges = np.histogram(data, bins=bins, range=(-1.0, 1.0), density=True)
        centers = 0.5 * (edges[:-1] + edges[1:])
        interpolated = np.interp(grid, centers, density)
        score = _shape_score(grid, interpolated)
        rows.append(
            {
                "estimator": f"histogram_{bins}",
                "shape_score": score,
                "modality": _shape_label(score),
            }
        )
    return rows


def _tail_window_rates(time: np.ndarray, survival: np.ndarray) -> dict:
    rows = []
    for low, high in ((0.05, 0.25), (0.10, 0.40), (0.25, 0.55)):
        mask = (survival >= low) & (survival <= high)
        fit = fit_exponential_rate(time[mask], survival[mask], minimum_points=6)
        rows.append(
            {
                "survival_window": [low, high],
                "rate": fit.rate,
                "r_squared": fit.r_squared,
                "n_points": fit.n_points,
            }
        )
    rates = [row["rate"] for row in rows if row["rate"] is not None]
    spread = (
        float((max(rates) - min(rates)) / np.mean(rates)) if len(rates) >= 2 else None
    )
    return {"windows": rows, "relative_rate_spread": spread}


def main() -> None:
    seed = get_seed()
    signal = simulate_lorenz(
        SignalConfig(
            SIGMA,
            burn_in=200.0,
            duration=10000.0,
            future_horizon=120.0,
            dt=0.01,
            rtol=2.0e-10,
            atol=2.0e-12,
        )
    )
    gamma_5000 = _gamma(signal.crossing_times, 5000.0)
    gamma_10000 = _gamma(signal.crossing_times, 10000.0)
    stationary_rows = []
    fine_results = {}
    for alpha in ALPHAS:
        coarse = compute_stationary_statistics(
            signal.sign, signal.dt, alpha, gamma_5000, analysis_duration=5000.0
        )
        fine = compute_stationary_statistics(
            signal.sign, signal.dt, alpha, gamma_10000, analysis_duration=10000.0
        )
        fine_results[alpha] = fine
        change = _relative_change(
            coarse.record["second_moment_y"], fine.record["second_moment_y"]
        )
        discrepancy = fine.record["rtp_second_relative_discrepancy"]
        se = fine.record["second_moment_se"]
        predicted = fine.record["rtp_second_moment_y"]
        z_score = (
            abs(fine.record["second_moment_y"] - predicted) / se
            if se is not None and predicted is not None
            else None
        )
        stationary_rows.append(
            {
                "alpha": alpha,
                "coarse_second_moment_y": coarse.record["second_moment_y"],
                "fine_second_moment_y": fine.record["second_moment_y"],
                "relative_change": change,
                "fine_second_moment_se": se,
                "rtp_second_moment_y": predicted,
                "rtp_relative_discrepancy": discrepancy,
                "z_score": z_score,
                "support_excess": fine.record["support_excess"],
                "symmetry_l1": fine.record["symmetry_l1"],
                "numerically_converged": bool(change is not None and change < 0.02),
                "collapse_falsified": bool(
                    change is not None
                    and change < 0.02
                    and discrepancy is not None
                    and abs(discrepancy) > 0.10
                    and z_score is not None
                    and z_score > 5.0
                ),
            }
        )

    modality_rows = []
    for alpha in (0.1, 0.25, 0.5, 0.75, 1.0):
        result = fine_results.get(alpha)
        if result is None:
            result = compute_stationary_statistics(
                signal.sign, signal.dt, alpha, gamma_10000, analysis_duration=10000.0
            )
        estimators = _estimator_diagnostics(result.sample_y)
        labels = {row["modality"] for row in estimators}
        modality_rows.append(
            {
                "alpha": alpha,
                "estimators": estimators,
                "stable": len(labels) == 1,
                "consensus": next(iter(labels)) if len(labels) == 1 else None,
            }
        )

    # Uniform candidate phases on a 0.5-time grid, randomly permuted once so
    # every refinement is a nested extension of the same natural-measure sample.
    horizon = 120.0
    horizon_steps = int(round(horizon / signal.dt))
    candidates = np.arange(0, signal.sign.size - horizon_steps, 50, dtype=int)
    rng = np.random.default_rng(seed + 3103)
    nested = rng.permutation(candidates)[:10240]
    stationary = fine_results[0.5]
    exponent_rows = []
    largest_fpt_arrays = None
    for size in (2560, 5120, 10240):
        phases = nested[:size]
        relaxation, _ = compute_relaxation_statistics(
            signal.sign,
            signal.dt,
            0.5,
            gamma_10000,
            stationary.sample_y,
            horizon=80.0,
            ensemble_size=size,
            rng=np.random.default_rng(seed),
            phase_indices=phases,
        )
        passage, fpt_arrays = compute_first_passage_statistics(
            signal.sign,
            signal.dt,
            0.5,
            gamma_10000,
            horizon=horizon,
            ensemble_size=size,
            rng=np.random.default_rng(seed),
            phase_indices=phases,
        )
        largest_fpt_arrays = fpt_arrays
        exponent_rows.append(
            {
                "ensemble_size": size,
                "relaxation_origin_rate": relaxation["initial_conditions"]["origin"][
                    "fitted_rate"
                ],
                "relaxation_origin_r2": relaxation["initial_conditions"]["origin"][
                    "fit_r_squared"
                ],
                "relaxation_half_edge_rate": relaxation["initial_conditions"][
                    "half_edge"
                ]["fitted_rate"],
                "relaxation_half_edge_r2": relaxation["initial_conditions"][
                    "half_edge"
                ]["fit_r_squared"],
                "first_passage_rate": passage["fitted_tail_rate"],
                "first_passage_r2": passage["tail_fit_r_squared"],
                "first_passage_rtp_rate": passage["rtp_predicted_tail_rate"],
                "first_passage_censored": passage["censored_fraction_symmetric"],
            }
        )

    exponent_changes = {
        key: _relative_change(exponent_rows[-2][key], exponent_rows[-1][key])
        for key in (
            "relaxation_origin_rate",
            "relaxation_half_edge_rate",
            "first_passage_rate",
        )
    }
    tail_diagnostic = _tail_window_rates(
        largest_fpt_arrays["time"], largest_fpt_arrays["survival_symmetric"]
    )
    save_summary(
        {
            "stage": 3,
            "purpose": "decisive_long_record_and_exponent_checks",
            "seed": seed,
            "sigma": SIGMA,
            "configuration": {
                "burn_in": 200.0,
                "duration": 10000.0,
                "future_horizon": 120.0,
                "dt": 0.01,
                "rtol": 2.0e-10,
                "atol": 2.0e-12,
            },
            "rate_convergence": {
                "gamma_5000": gamma_5000,
                "gamma_10000": gamma_10000,
                "relative_change": _relative_change(gamma_5000, gamma_10000),
            },
            "stationary": stationary_rows,
            "modality_estimators": modality_rows,
            "exponents": exponent_rows,
            "exponent_relative_changes_5120_to_10240": exponent_changes,
            "first_passage_tail_window_diagnostic": tail_diagnostic,
            "gates": {
                "rate_two_percent_pass": bool(
                    _relative_change(gamma_5000, gamma_10000) < 0.02
                ),
                "all_stationary_moments_two_percent_pass": bool(
                    all(row["numerically_converged"] for row in stationary_rows)
                ),
                "all_exponents_five_percent_pass": bool(
                    all(value is not None and value < 0.05 for value in exponent_changes.values())
                ),
                "first_passage_exponential_tail_supported": bool(
                    exponent_rows[-1]["first_passage_r2"] is not None
                    and exponent_rows[-1]["first_passage_r2"] >= 0.98
                    and tail_diagnostic["relative_rate_spread"] is not None
                    and tail_diagnostic["relative_rate_spread"] < 0.10
                ),
                "stable_modality_points": [
                    row["alpha"] for row in modality_rows if row["stable"]
                ],
                "unstable_modality_points": [
                    row["alpha"] for row in modality_rows if not row["stable"]
                ],
                "collapse_falsified_alphas": [
                    row["alpha"] for row in stationary_rows if row["collapse_falsified"]
                ],
            },
        }
    )


if __name__ == "__main__":
    main()
