"""Fine-grid and threshold-stability validation of the first-passage tail."""

from __future__ import annotations

import numpy as np

from rpipe.helpers.io import get_seed, save_summary
from work.first_passage_statistics import _first_passage_times, compute_first_passage_statistics
from work.lorenz_signal import SignalConfig, simulate_lorenz
from work.stage3_decisive import _relative_change, _tail_window_rates


def main() -> None:
    seed = get_seed()
    sigma = float(np.sqrt(50.0))
    alpha = 0.5
    signal = simulate_lorenz(
        SignalConfig(
            sigma,
            burn_in=200.0,
            duration=4000.0,
            future_horizon=120.0,
            dt=0.01,
            rtol=2.0e-10,
            atol=2.0e-12,
        )
    )
    gamma = float(1.0 / np.mean(np.diff(signal.crossing_times[signal.crossing_times <= 4000.0])))
    horizon = 120.0
    horizon_steps = int(round(horizon / signal.dt))
    candidates = np.arange(0, signal.sign.size - horizon_steps, 25, dtype=int)
    nested = np.random.default_rng(seed + 8821).permutation(candidates)[:10240]
    rows = []
    largest_arrays = None
    for size in (5120, 10240):
        record, arrays = compute_first_passage_statistics(
            signal.sign,
            signal.dt,
            alpha,
            gamma,
            horizon=horizon,
            ensemble_size=size,
            rng=np.random.default_rng(seed),
            phase_indices=nested[:size],
        )
        largest_arrays = arrays
        rows.append(
            {
                "ensemble_size": size,
                "rate": record["fitted_tail_rate"],
                "r_squared": record["tail_fit_r_squared"],
                "fit_window": record["tail_fit_window"],
                "rtp_rate": record["rtp_predicted_tail_rate"],
                "censored_fraction": record["censored_fraction_symmetric"],
            }
        )

    phases = nested[:10240]
    paths = signal.sign[phases[:, None] + np.arange(horizon_steps + 1)[None, :]]
    initial = paths[:, 0]
    sector_times = []
    for direction in (-1, 1):
        values = _first_passage_times(paths[initial == direction], 2.0 * alpha, signal.dt)
        sector_times.append(values[np.isfinite(values)])
    balanced_count = min(values.size for values in sector_times)
    balanced = np.concatenate([values[:balanced_count] for values in sector_times])
    threshold_rows = []
    for quantile in (0.50, 0.65, 0.80):
        threshold = float(np.quantile(balanced, quantile))
        excess = balanced[balanced > threshold] - threshold
        rate = float(1.0 / np.mean(excess))
        standard_error = float(rate / np.sqrt(excess.size))
        threshold_rows.append(
            {
                "quantile": quantile,
                "threshold": threshold,
                "tail_count": int(excess.size),
                "rate": rate,
                "standard_error": standard_error,
            }
        )
    threshold_rates = [row["rate"] for row in threshold_rows]
    threshold_spread = float((max(threshold_rates) - min(threshold_rates)) / np.mean(threshold_rates))
    window_diagnostic = _tail_window_rates(
        largest_arrays["time"], largest_arrays["survival_symmetric"]
    )
    measured = rows[-1]["rate"]
    predicted = rows[-1]["rtp_rate"]
    conservative_se = max(row["standard_error"] for row in threshold_rows)
    save_summary(
        {
            "stage": 3,
            "purpose": "fine_grid_first_passage_tail_validation",
            "seed": seed,
            "sigma": sigma,
            "alpha": alpha,
            "gamma_eff": gamma,
            "ensemble_refinement": rows,
            "ensemble_relative_change": _relative_change(rows[0]["rate"], rows[1]["rate"]),
            "tail_window_diagnostic": window_diagnostic,
            "threshold_exponential_mle": threshold_rows,
            "threshold_rate_relative_spread": threshold_spread,
            "rtp_discrepancy": {
                "measured_rate": measured,
                "predicted_rate": predicted,
                "relative_discrepancy": float((measured - predicted) / predicted),
                "conservative_standard_error": conservative_se,
                "z_score": float(abs(measured - predicted) / conservative_se),
            },
            "gates": {
                "five_percent_ensemble_convergence": bool(
                    _relative_change(rows[0]["rate"], rows[1]["rate"]) < 0.05
                ),
                "exponential_tail_supported": bool(
                    rows[-1]["r_squared"] >= 0.98
                    and window_diagnostic["relative_rate_spread"] is not None
                    and window_diagnostic["relative_rate_spread"] < 0.10
                    and threshold_spread < 0.10
                ),
                "rtp_tail_falsified": bool(
                    _relative_change(rows[0]["rate"], rows[1]["rate"]) < 0.05
                    and rows[-1]["r_squared"] >= 0.98
                    and window_diagnostic["relative_rate_spread"] is not None
                    and window_diagnostic["relative_rate_spread"] < 0.10
                    and threshold_spread < 0.10
                    and abs(measured - predicted) / predicted > 0.10
                    and abs(measured - predicted) / conservative_se > 5.0
                ),
            },
        }
    )


if __name__ == "__main__":
    main()
