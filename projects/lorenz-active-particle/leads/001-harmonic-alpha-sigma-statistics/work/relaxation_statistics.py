"""Natural-measure ensemble relaxation from the two agreed initial positions."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.stats import wasserstein_distance

from work.harmonic_particle import (
    fit_exponential_rate,
    natural_phase_indices,
    propagate_at_times,
    rtp_relaxation_rates,
)


def _record_steps(horizon: float, dt: float) -> np.ndarray:
    final = int(horizon / dt)
    dense = np.linspace(0, final, 81, dtype=int)
    logarithmic = np.geomspace(1, max(2, final), 50).astype(int)
    return np.unique(np.concatenate(([0], dense, logarithmic, [final])))


def _rate_window(time: np.ndarray, observable: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    finite = np.isfinite(observable) & (observable > 1.0e-10)
    if not finite[0]:
        return time[finite], observable[finite]
    initial = float(observable[0])
    tail = observable[-max(6, observable.size // 6) :]
    noise_floor = float(np.nanmedian(tail[np.isfinite(tail)])) if np.any(np.isfinite(tail)) else 0.0
    lower = max(0.06 * initial, 2.5 * noise_floor)
    upper = 0.96 * initial
    mask = finite & (time > 0.0) & (observable >= lower) & (observable <= upper)
    if np.count_nonzero(mask) < 8:
        mask = finite & (time > 0.0) & (observable >= 0.03 * initial) & (observable <= 0.99 * initial)
    indices = np.flatnonzero(mask)
    if indices.size >= 2:
        contiguous = np.arange(indices[0], indices[-1] + 1)
        contiguous = contiguous[finite[contiguous]]
        return time[contiguous], observable[contiguous]
    return time[mask], observable[mask]


def compute_relaxation_statistics(
    sign: np.ndarray,
    dt: float,
    alpha: float,
    gamma_eff: float | None,
    stationary_y: np.ndarray,
    *,
    horizon: float,
    ensemble_size: int,
    rng: np.random.Generator,
    phase_indices: np.ndarray | None = None,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    mu = 2.0 * alpha
    steps = _record_steps(horizon, dt)
    horizon_steps = int(steps[-1])
    if phase_indices is None:
        phases = natural_phase_indices(sign.size, horizon_steps, ensemble_size, rng)
    else:
        phases = np.sort(np.asarray(phase_indices, dtype=int))
        if phases.size == 0 or phases.min() < 0 or phases.max() + horizon_steps >= sign.size:
            raise ValueError("Invalid phase_indices for the requested relaxation horizon.")
    offsets = np.arange(horizon_steps + 1)
    paths = sign[phases[:, None] + offsets[None, :]]
    time = steps * dt
    stationary_mean = float(np.mean(stationary_y))
    stationary_second = float(np.mean(stationary_y**2))
    rates = rtp_relaxation_rates(mu, gamma_eff) if gamma_eff is not None else None
    results: dict[str, Any] = {}
    arrays: dict[str, np.ndarray] = {"time": time}
    bins = np.linspace(-1.0, 1.0, 81)
    for label, y0 in (("origin", 0.0), ("half_edge", 0.5)):
        trajectories = propagate_at_times(paths, mu, dt, y0, steps)
        means = np.mean(trajectories, axis=1)
        seconds = np.mean(trajectories**2, axis=1)
        wasserstein = np.asarray(
            [wasserstein_distance(row, stationary_y[:: max(1, stationary_y.size // 4000)]) for row in trajectories]
        )
        densities = np.asarray([np.histogram(row, bins=bins, density=True)[0] for row in trajectories])
        observable = (
            np.abs(seconds - stationary_second)
            if label == "origin"
            else np.abs(means - stationary_mean)
        )
        fit_time, fit_observable = _rate_window(time, observable)
        fit = fit_exponential_rate(fit_time, fit_observable)
        predicted = rates[label if label == "origin" else "generic"] if rates else None
        results[label] = {
            "initial_y": y0,
            "fitted_rate": fit.rate,
            "fit_r_squared": fit.r_squared,
            "fit_accepted_preliminary": bool(
                fit.rate is not None and fit.r_squared is not None and fit.r_squared >= 0.8
            ),
            "fit_window": [fit.start_time, fit.end_time],
            "rtp_predicted_rate": predicted,
            "relative_rate_discrepancy": (
                (fit.rate - predicted) / predicted
                if fit.rate is not None and predicted is not None
                else None
            ),
            "final_mean_y": float(means[-1]),
            "final_second_moment_y": float(seconds[-1]),
            "final_wasserstein_y": float(wasserstein[-1]),
            "minimum_wasserstein_y": float(np.min(wasserstein)),
        }
        arrays[f"{label}_mean"] = means
        arrays[f"{label}_second"] = seconds
        arrays[f"{label}_wasserstein"] = wasserstein
        arrays[f"{label}_density"] = densities
        rate = np.full(time.size - 1, np.nan)
        valid = (observable[:-1] > 0.0) & (observable[1:] > 0.0)
        rate[valid] = -np.diff(np.log(observable))[valid] / np.diff(time)[valid]
        arrays[f"{label}_local_rate_time"] = 0.5 * (time[:-1] + time[1:])
        arrays[f"{label}_local_rate"] = rate
    arrays["density_edges"] = bins
    return {
        "alpha": float(alpha),
        "mu": float(mu),
        "ensemble_size": int(phases.size),
        "horizon": float(horizon),
        "phase_min": int(phases[0]),
        "phase_max": int(phases[-1]),
        "initial_conditions": results,
    }, arrays

