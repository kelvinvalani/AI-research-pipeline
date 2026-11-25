"""Exact harmonic filtering and harmonic-RTP benchmark formulas."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import mpmath as mp
import numpy as np
from scipy.optimize import brentq
from scipy.special import beta, hyp2f1

U = 3.0 * np.sqrt(3.0)


@dataclass(frozen=True)
class ExponentialFit:
    rate: float | None
    r_squared: float | None
    start_time: float | None
    end_time: float | None
    n_points: int


def normalized_filter(sign: np.ndarray, mu: float, dt: float, y0: float = 0.0) -> np.ndarray:
    """Exact update for a sign held constant on each uniform output interval."""
    sign = np.asarray(sign, dtype=float)
    result = np.empty(sign.size, dtype=float)
    result[0] = y0
    decay = float(np.exp(-mu * dt))
    forcing = 1.0 - decay
    for idx in range(1, sign.size):
        result[idx] = decay * result[idx - 1] + forcing * sign[idx - 1]
    return result


def propagate_at_times(
    sign_paths: np.ndarray,
    mu: float,
    dt: float,
    y0: float,
    record_steps: np.ndarray,
) -> np.ndarray:
    """Propagate many natural-measure phases and retain only requested times."""
    paths = np.asarray(sign_paths, dtype=float)
    steps = np.asarray(record_steps, dtype=int)
    if paths.ndim != 2 or steps[0] != 0 or steps[-1] >= paths.shape[1]:
        raise ValueError("Invalid sign paths or record steps.")
    out = np.empty((steps.size, paths.shape[0]), dtype=float)
    y = np.full(paths.shape[0], y0, dtype=float)
    out[0] = y
    decay = float(np.exp(-mu * dt))
    forcing = 1.0 - decay
    target = 1
    for step in range(1, int(steps[-1]) + 1):
        y = decay * y + forcing * paths[:, step - 1]
        if target < steps.size and step == steps[target]:
            out[target] = y
            target += 1
    return out


def natural_phase_indices(
    available_steps: int,
    horizon_steps: int,
    ensemble_size: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Uniformly sample post-burn-in phases that have a complete future sign record."""
    last_start = available_steps - horizon_steps - 1
    if last_start < 1:
        raise ValueError("The Lorenz record is shorter than the requested future horizon.")
    size = min(int(ensemble_size), last_start + 1)
    return np.sort(rng.choice(last_start + 1, size=size, replace=False))


def rtp_density_y(y: np.ndarray, mu: float, gamma: float) -> np.ndarray:
    a = gamma / mu
    values = np.asarray(y, dtype=float)
    density = np.zeros_like(values)
    inside = np.abs(values) < 1.0
    density[inside] = np.power(1.0 - values[inside] ** 2, a - 1.0) / beta(0.5, a)
    return density


def rtp_moments_y(mu: float, gamma: float) -> dict[str, float]:
    second = mu / (mu + 2.0 * gamma)
    fourth = 3.0 * mu * mu / ((mu + 2.0 * gamma) * (3.0 * mu + 2.0 * gamma))
    return {"mean": 0.0, "second": second, "fourth": fourth}


def rtp_shape_boundary_alpha(gamma: float) -> float:
    return 0.5 * gamma


def rtp_relaxation_rates(mu: float, gamma: float) -> dict[str, float]:
    return {"generic": mu, "origin": min(mu + 2.0 * gamma, 2.0 * mu)}


def _first_passage_root_function(theta: float, mu: float, gamma: float) -> float:
    return float(hyp2f1(-theta / mu, (2.0 * gamma - theta) / mu, (gamma - theta) / mu, 0.5))


@lru_cache(maxsize=512)
def rtp_first_passage_rate(mu: float, gamma: float) -> float | None:
    """Lowest physical root of Dhar et al. Eq. (88), excluding hypergeometric poles."""
    if mu <= 0.0 or gamma <= 0.0:
        return None
    upper = mu * (1.0 - 2.0e-8)
    grid = np.linspace(max(1.0e-9, 1.0e-8 * min(mu, gamma)), upper, 4097)
    values = np.asarray([_first_passage_root_function(x, mu, gamma) for x in grid])
    finite = np.isfinite(values) & (np.abs(values) < 1.0e12)
    for idx in range(grid.size - 1):
        if not (finite[idx] and finite[idx + 1]):
            continue
        if values[idx] == 0.0:
            return float(grid[idx])
        if values[idx] * values[idx + 1] < 0.0:
            root = brentq(_first_passage_root_function, grid[idx], grid[idx + 1], args=(mu, gamma))
            if abs(root - gamma) / max(gamma, 1.0e-15) < 1.0e-7:
                continue
            # scipy.special.hyp2f1 can exhibit spurious sign changes for large
            # gamma/mu through catastrophic cancellation.  Accept a candidate
            # only after an independent high-precision residual evaluation.
            with mp.workdps(50):
                q = mp.mpf(str(root / mu))
                g = mp.mpf(str(gamma / mu))
                residual = mp.hyp2f1(-q, 2 * g - q, g - q, mp.mpf("0.5"))
            if not mp.isfinite(residual) or abs(residual) > mp.mpf("1e-8"):
                continue
            return float(root)

    # High-precision fallback for regimes where the double-precision function
    # is inaccurate over a whole interval (notably gamma/mu >> 1).  Split the
    # physical interval at hypergeometric parameter poles so a discontinuity is
    # never mistaken for a zero.
    with mp.workdps(50):
        g = mp.mpf(str(gamma / mu))
        eps = mp.mpf("1e-12")
        poles = []
        n = 0
        while g + n < 1:
            if g + n > 0:
                poles.append(g + n)
            n += 1
        bounds = [eps]
        for pole in poles:
            bounds.extend((pole - eps, pole + eps))
        bounds.append(1 - eps)
        intervals = list(zip(bounds[::2], bounds[1::2], strict=True))

        def function(q):
            return mp.hyp2f1(-q, 2 * g - q, g - q, mp.mpf("0.5"))

        for left, right in intervals:
            grid_mp = [left + (right - left) * k / 128 for k in range(129)]
            previous_q = grid_mp[0]
            previous_value = function(previous_q)
            for q in grid_mp[1:]:
                value = function(q)
                if mp.isfinite(previous_value) and mp.isfinite(value) and previous_value * value < 0:
                    root_q = mp.findroot(
                        function,
                        (previous_q, q),
                        solver="bisect",
                        tol=mp.mpf("1e-35"),
                        verify=False,
                    )
                    if all(abs(root_q - pole) > mp.mpf("1e-9") for pole in poles):
                        return float(mp.mpf(str(mu)) * root_q)
                previous_q, previous_value = q, value
    return None


def fit_exponential_rate(
    time: np.ndarray,
    observable: np.ndarray,
    *,
    minimum_points: int = 6,
    min_value: float = 1.0e-10,
) -> ExponentialFit:
    time = np.asarray(time, dtype=float)
    values = np.asarray(observable, dtype=float)
    mask = np.isfinite(values) & (values > min_value)
    if np.count_nonzero(mask) < minimum_points:
        return ExponentialFit(None, None, None, None, int(np.count_nonzero(mask)))
    x = time[mask]
    y = np.log(values[mask])
    slope, intercept = np.polyfit(x, y, 1)
    predicted = slope * x + intercept
    residual = float(np.sum((y - predicted) ** 2))
    total = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = 1.0 - residual / total if total > 0.0 else 1.0
    rate = float(-slope)
    return ExponentialFit(
        rate if rate > 0.0 else None,
        float(r_squared),
        float(x[0]),
        float(x[-1]),
        int(x.size),
    )


def x_from_y(y: np.ndarray | float, alpha: float) -> np.ndarray:
    return np.asarray(y) * U / (2.0 * alpha)

