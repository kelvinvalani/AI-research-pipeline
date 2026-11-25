"""Long-record Stage 3 refinement diagnostics for the strongest Stage 2 discrepancy."""

from __future__ import annotations

import numpy as np

from rpipe.helpers.io import get_seed, save_summary
from work.first_passage_statistics import compute_first_passage_statistics
from work.lorenz_signal import SignalConfig, simulate_lorenz
from work.relaxation_statistics import compute_relaxation_statistics
from work.stationary_statistics import compute_stationary_statistics


SIGMA = float(np.sqrt(50.0))
ALPHAS = (0.05, 0.1, 0.25, 0.5, 1.0, 5.0)


def _relative_change(coarse: float, fine: float) -> float:
    return float(abs(coarse - fine) / max(abs(fine), 1.0e-15))


def _rate(crossings: np.ndarray, start: float, stop: float) -> float | None:
    selected = crossings[(crossings >= start) & (crossings <= stop)]
    runs = np.diff(selected)
    return float(1.0 / np.mean(runs)) if runs.size else None


def _stationary_rows(sign: np.ndarray, dt: float, duration: float, gamma: float) -> list[dict]:
    rows = []
    for alpha in ALPHAS:
        record = compute_stationary_statistics(
            sign, dt, alpha, gamma, analysis_duration=duration
        ).record
        rows.append(
            {
                "alpha": alpha,
                "second_moment_y": record["second_moment_y"],
                "second_moment_se": record["second_moment_se"],
                "fourth_moment_y": record["fourth_moment_y"],
                "rtp_second_moment_y": record["rtp_second_moment_y"],
                "rtp_second_relative_discrepancy": record[
                    "rtp_second_relative_discrepancy"
                ],
                "symmetry_l1": record["symmetry_l1"],
                "support_excess": record["support_excess"],
                "modality": record["modality"],
                "shape_score": record["shape_score"],
            }
        )
    return rows


def main() -> None:
    seed = get_seed()
    signal = simulate_lorenz(
        SignalConfig(
            SIGMA,
            burn_in=50.0,
            duration=4950.0,
            future_horizon=120.0,
            dt=0.005,
            rtol=2.0e-10,
            atol=2.0e-12,
        )
    )

    # Actual burn-ins 50, 100, and 200 use one trajectory and a common endpoint.
    burn_rows = []
    for offset in (0.0, 50.0, 150.0):
        first = int(round(offset / signal.dt))
        available_duration = 4950.0 - offset
        gamma = _rate(signal.crossing_times, offset, 4950.0)
        stationary = compute_stationary_statistics(
            signal.sign[first:], signal.dt, 0.05, gamma, analysis_duration=available_duration
        ).record
        burn_rows.append(
            {
                "burn_in": 50.0 + offset,
                "gamma_eff": gamma,
                "second_moment_y_alpha_0p05": stationary["second_moment_y"],
            }
        )

    # Nested prefixes after an actual burn-in of 200.
    start = int(round(150.0 / signal.dt))
    crossings = signal.crossing_times - 150.0
    crossings = crossings[crossings >= 0.0]
    post = signal.sign[start:]
    length_rows = []
    length_stationary: dict[float, list[dict]] = {}
    for duration in (1200.0, 2400.0, 4800.0):
        count = int(round(duration / signal.dt)) + 1
        gamma = _rate(crossings, 0.0, duration)
        rows = _stationary_rows(post[:count], signal.dt, duration, gamma)
        length_rows.append({"duration": duration, "gamma_eff": gamma})
        length_stationary[duration] = rows

    # Timestep refinement by downsampling a single fine Lorenz trajectory.  This
    # holds the chaotic realization fixed and isolates sign-grid/filter error.
    timestep_rows = []
    gamma_fine = length_rows[-1]["gamma_eff"]
    fine_count = int(round(4800.0 / signal.dt)) + 1
    fine_sign = post[:fine_count]
    for factor in (4, 2, 1):
        dt = signal.dt * factor
        sampled = fine_sign[::factor]
        timestep_rows.append(
            {
                "dt": dt,
                "stationary": _stationary_rows(sampled, dt, 4800.0, gamma_fine),
            }
        )

    # ODE tolerance refinement on a common pre-divergence interval.
    tolerance_rows = []
    for rtol, atol in ((2.0e-9, 2.0e-11), (2.0e-10, 2.0e-12), (2.0e-11, 2.0e-13)):
        short = simulate_lorenz(
            SignalConfig(
                SIGMA,
                burn_in=0.0,
                duration=20.0,
                future_horizon=0.0,
                dt=0.005,
                rtol=rtol,
                atol=atol,
            )
        )
        tolerance_rows.append(
            {
                "rtol": rtol,
                "atol": atol,
                "crossing_times": short.crossing_times.tolist(),
            }
        )

    # Ensemble-size refinement for both approved initial conditions and FPT.
    stationary = compute_stationary_statistics(
        fine_sign, signal.dt, 0.5, gamma_fine, analysis_duration=4800.0
    )
    ensemble_rows = []
    for size in (320, 640, 1280, 2560):
        relaxation, _ = compute_relaxation_statistics(
            post,
            signal.dt,
            0.5,
            gamma_fine,
            stationary.sample_y,
            horizon=80.0,
            ensemble_size=size,
            rng=np.random.default_rng(seed + size),
        )
        first_passage, _ = compute_first_passage_statistics(
            post,
            signal.dt,
            0.5,
            gamma_fine,
            horizon=120.0,
            ensemble_size=size,
            rng=np.random.default_rng(seed + 10000 + size),
        )
        ensemble_rows.append(
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
                "first_passage_rate": first_passage["fitted_tail_rate"],
                "first_passage_r2": first_passage["tail_fit_r_squared"],
                "first_passage_censored": first_passage["censored_fraction_symmetric"],
            }
        )

    length_rate_change = _relative_change(
        length_rows[-2]["gamma_eff"], length_rows[-1]["gamma_eff"]
    )
    length_moment_changes = {
        str(alpha): _relative_change(
            length_stationary[2400.0][idx]["second_moment_y"],
            length_stationary[4800.0][idx]["second_moment_y"],
        )
        for idx, alpha in enumerate(ALPHAS)
    }
    timestep_moment_changes = {
        str(alpha): _relative_change(
            timestep_rows[-2]["stationary"][idx]["second_moment_y"],
            timestep_rows[-1]["stationary"][idx]["second_moment_y"],
        )
        for idx, alpha in enumerate(ALPHAS)
    }
    burn_rate_change = _relative_change(burn_rows[-2]["gamma_eff"], burn_rows[-1]["gamma_eff"])
    burn_moment_change = _relative_change(
        burn_rows[-2]["second_moment_y_alpha_0p05"],
        burn_rows[-1]["second_moment_y_alpha_0p05"],
    )
    save_summary(
        {
            "stage": 3,
            "purpose": "long_record_refinement",
            "seed": seed,
            "sigma": SIGMA,
            "alpha_range_checked": [min(ALPHAS), max(ALPHAS)],
            "burn_in": burn_rows,
            "trajectory_length": length_rows,
            "trajectory_length_stationary": length_stationary,
            "timestep": timestep_rows,
            "ode_tolerance": tolerance_rows,
            "ensemble_size": ensemble_rows,
            "gates": {
                "burn_rate_relative_change": burn_rate_change,
                "burn_moment_relative_change": burn_moment_change,
                "length_rate_relative_change": length_rate_change,
                "length_second_moment_relative_changes": length_moment_changes,
                "timestep_second_moment_relative_changes": timestep_moment_changes,
                "burn_and_length_two_percent_pass": bool(
                    burn_rate_change < 0.02
                    and burn_moment_change < 0.02
                    and length_rate_change < 0.02
                    and max(length_moment_changes.values()) < 0.02
                ),
                "timestep_two_percent_pass": bool(
                    max(timestep_moment_changes.values()) < 0.02
                ),
            },
        }
    )


if __name__ == "__main__":
    main()
