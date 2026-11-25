"""Censored first-passage statistics from the agreed half-edge initial position."""

from __future__ import annotations

from typing import Any

import numpy as np

from work.harmonic_particle import fit_exponential_rate, natural_phase_indices, rtp_first_passage_rate


def _first_passage_times(sign_paths: np.ndarray, mu: float, dt: float) -> np.ndarray:
    count, steps = sign_paths.shape
    times = np.full(count, np.inf, dtype=float)
    active = np.ones(count, dtype=bool)
    y = np.full(count, 0.5, dtype=float)
    decay = float(np.exp(-mu * dt))
    forcing = 1.0 - decay
    for step in range(1, steps):
        if not np.any(active):
            break
        previous = y.copy()
        drive = sign_paths[:, step - 1]
        y[active] = decay * y[active] + forcing * drive[active]
        hit = active & (y <= 0.0)
        if np.any(hit):
            local = np.log1p(previous[hit]) / mu
            times[hit] = (step - 1) * dt + np.clip(local, 0.0, dt)
            active[hit] = False
    return times


def _survival(times: np.ndarray, grid: np.ndarray) -> np.ndarray:
    if times.size == 0:
        return np.full(grid.size, np.nan)
    return np.asarray([np.mean(times > time) for time in grid], dtype=float)


def _quantile_from_survival(time: np.ndarray, survival: np.ndarray, quantile: float) -> float | None:
    target = 1.0 - quantile
    hits = np.flatnonzero(survival <= target)
    if hits.size == 0:
        return None
    idx = int(hits[0])
    if idx == 0:
        return float(time[0])
    q0, q1 = survival[idx - 1], survival[idx]
    if q0 == q1:
        return float(time[idx])
    fraction = (q0 - target) / (q0 - q1)
    return float(time[idx - 1] + fraction * (time[idx] - time[idx - 1]))


def _tail_fit(time: np.ndarray, survival: np.ndarray):
    mask = (
        np.isfinite(survival)
        & (survival >= 0.04)
        & (survival <= 0.55)
        & (time >= 0.15 * time[-1])
    )
    if np.count_nonzero(mask) < 6:
        mask = np.isfinite(survival) & (survival > 0.02) & (survival < 0.85)
    return fit_exponential_rate(time[mask], survival[mask], minimum_points=6)


def compute_first_passage_statistics(
    sign: np.ndarray,
    dt: float,
    alpha: float,
    gamma_eff: float | None,
    *,
    horizon: float,
    ensemble_size: int,
    rng: np.random.Generator,
    phase_indices: np.ndarray | None = None,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    mu = 2.0 * alpha
    horizon_steps = int(horizon / dt)
    if phase_indices is None:
        phases = natural_phase_indices(sign.size, horizon_steps, ensemble_size, rng)
    else:
        phases = np.sort(np.asarray(phase_indices, dtype=int))
        if phases.size == 0 or phases.min() < 0 or phases.max() + horizon_steps >= sign.size:
            raise ValueError("Invalid phase_indices for the requested first-passage horizon.")
    offsets = np.arange(horizon_steps + 1)
    paths = sign[phases[:, None] + offsets[None, :]]
    initial_sign = paths[:, 0]
    # A fixed 241-point grid undersamples fast tails when the censoring horizon
    # is long (for example, a rate O(1) with horizon 120).  Keep the survival
    # grid at 0.1 time units or finer so local-slope and competing-window checks
    # contain enough points without changing the underlying passage times.
    grid_points = max(241, int(np.ceil(horizon / 0.1)) + 1)
    grid = np.linspace(0.0, horizon, grid_points)
    sector_times: dict[str, np.ndarray] = {}
    sector_survival: dict[str, np.ndarray] = {}
    sector_records: dict[str, Any] = {}
    for label, direction in (("plus", 1), ("minus", -1)):
        selected = paths[initial_sign == direction]
        passage = _first_passage_times(selected, mu, dt)
        sector_times[label] = passage
        sector_survival[label] = _survival(passage, grid)
        finite = passage[np.isfinite(passage)]
        sector_records[label] = {
            "ensemble_size": int(passage.size),
            "event_count": int(finite.size),
            "censored_fraction": float(1.0 - finite.size / max(1, passage.size)),
            "finite_mean": float(np.mean(finite)) if finite.size else None,
        }
    symmetric = 0.5 * (sector_survival["plus"] + sector_survival["minus"])
    fit = _tail_fit(grid, symmetric)
    predicted = rtp_first_passage_rate(mu, gamma_eff) if gamma_eff is not None else None
    density = -np.diff(symmetric) / np.diff(grid)
    density_time = 0.5 * (grid[1:] + grid[:-1])
    restricted_mean = float(np.trapezoid(symmetric, grid))
    total_censored = float(symmetric[-1])
    local_rate = np.full(grid.size - 1, np.nan)
    valid = (symmetric[:-1] > 0.0) & (symmetric[1:] > 0.0)
    log_survival = np.full(symmetric.size, np.nan)
    positive = symmetric > 0.0
    log_survival[positive] = np.log(symmetric[positive])
    local_rate[valid] = -np.diff(log_survival)[valid] / np.diff(grid)[valid]
    record = {
        "alpha": float(alpha),
        "mu": float(mu),
        "initial_y": 0.5,
        "horizon": float(horizon),
        "symmetric_ensemble_definition": "equal-weight average of initial Lorenz sign sectors",
        "sectors": sector_records,
        "censored_fraction_symmetric": total_censored,
        "restricted_mean": restricted_mean,
        "mean_first_passage": restricted_mean if total_censored == 0.0 else None,
        "quantiles": {
            str(q): _quantile_from_survival(grid, symmetric, q) for q in (0.1, 0.25, 0.5, 0.75, 0.9)
        },
        "fitted_tail_rate": fit.rate,
        "tail_fit_r_squared": fit.r_squared,
        "tail_fit_window": [fit.start_time, fit.end_time],
        "rtp_predicted_tail_rate": predicted,
        "rtp_tail_relative_discrepancy": (
            (fit.rate - predicted) / predicted
            if fit.rate is not None and predicted is not None
            else None
        ),
    }
    arrays = {
        "time": grid,
        "survival_plus": sector_survival["plus"],
        "survival_minus": sector_survival["minus"],
        "survival_symmetric": symmetric,
        "density_time": density_time,
        "first_passage_density": density,
        "local_tail_rate_time": density_time,
        "local_tail_rate": local_rate,
    }
    return record, arrays

