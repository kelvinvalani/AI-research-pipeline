"""Lorenz direction signals, event-resolved reversals, and attractor diagnostics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from scipy.integrate import solve_ivp
from scipy.signal import find_peaks
from scipy.stats import kstest

R = 28.0
B = 8.0 / 3.0
U = 3.0 * np.sqrt(3.0)


@dataclass(frozen=True)
class SignalConfig:
    sigma: float
    burn_in: float = 100.0
    duration: float = 400.0
    future_horizon: float = 80.0
    dt: float = 0.01
    rtol: float = 2.0e-10
    atol: float = 2.0e-12
    initial: tuple[float, float, float] = (1.0, 1.0, 1.0)


@dataclass
class LorenzSignal:
    config: SignalConfig
    time: np.ndarray
    states: np.ndarray
    sign: np.ndarray
    crossing_times: np.ndarray
    crossing_directions: np.ndarray

    @property
    def dt(self) -> float:
        return self.config.dt

    def summary(self, max_correlation_time: float = 30.0) -> dict[str, Any]:
        runs = np.diff(self.crossing_times)
        gamma = float(1.0 / np.mean(runs)) if runs.size else None
        serial = _lag_one_correlation(runs)
        if runs.size >= 8:
            ks = kstest(runs, "expon", args=(0.0, float(np.mean(runs))))
            ks_stat, ks_pvalue = float(ks.statistic), float(ks.pvalue)
        else:
            ks_stat = ks_pvalue = None
        lag, corr = sign_autocorrelation(self.sign, self.dt, max_correlation_time)
        corr_time = integral_correlation_time(lag, corr)
        return {
            "sigma": self.config.sigma,
            "configuration": asdict(self.config),
            "attractor_class": classify_attractor(self),
            "n_crossings": int(self.crossing_times.size),
            "gamma_eff": gamma,
            "mean_run_time": float(np.mean(runs)) if runs.size else None,
            "run_time_std": float(np.std(runs, ddof=1)) if runs.size > 1 else None,
            "run_time_cv": (
                float(np.std(runs, ddof=1) / np.mean(runs)) if runs.size > 1 else None
            ),
            "run_quantiles": (
                np.quantile(runs, [0.05, 0.25, 0.5, 0.75, 0.95]).tolist()
                if runs.size
                else []
            ),
            "run_serial_correlation_lag1": serial,
            "exponential_ks_statistic": ks_stat,
            "exponential_ks_pvalue": ks_pvalue,
            "mean_sign": float(np.mean(self.sign)),
            "integral_correlation_time": corr_time,
            "free_effective_diffusivity_green_kubo": float(U * U * corr_time),
            "sign_correlation_lags": lag[:: max(1, len(lag) // 80)].tolist(),
            "sign_correlation": corr[:: max(1, len(corr) // 80)].tolist(),
        }


def lorenz_rhs(_: float, state: np.ndarray, sigma: float) -> tuple[float, float, float]:
    x, y, z = state
    return sigma * (y - x), R * x - y - x * z, x * y - B * z


def _x_crossing(_: float, state: np.ndarray, __: float) -> float:
    return float(state[0])


_x_crossing.terminal = False
_x_crossing.direction = 0


def _continued_sign(values: np.ndarray) -> np.ndarray:
    signs = np.sign(values).astype(np.int8)
    if signs[0] == 0:
        nonzero = np.flatnonzero(signs)
        signs[0] = signs[nonzero[0]] if nonzero.size else 1
    for idx in np.flatnonzero(signs == 0):
        signs[idx] = signs[idx - 1]
    return signs


def simulate_lorenz(config: SignalConfig) -> LorenzSignal:
    """Integrate the agreed Lorenz model and retain its post-burn-in natural-measure record."""
    total = config.burn_in + config.duration + config.future_horizon
    n_out = int(np.floor(total / config.dt)) + 1
    t_eval = np.linspace(0.0, config.dt * (n_out - 1), n_out)
    solution = solve_ivp(
        lorenz_rhs,
        (0.0, float(t_eval[-1])),
        np.asarray(config.initial, dtype=float),
        args=(config.sigma,),
        method="DOP853",
        t_eval=t_eval,
        events=_x_crossing,
        rtol=config.rtol,
        atol=config.atol,
        max_step=2.0 * config.dt,
    )
    if not solution.success:
        raise RuntimeError(f"Lorenz integration failed at sigma={config.sigma}: {solution.message}")
    keep = solution.t >= config.burn_in - 0.25 * config.dt
    time = solution.t[keep] - config.burn_in
    states = solution.y[:, keep].T
    crossings = np.asarray(solution.t_events[0], dtype=float)
    crossings = crossings[crossings >= config.burn_in] - config.burn_in
    event_states = np.asarray(solution.y_events[0], dtype=float).reshape((-1, 3))
    event_states = event_states[solution.t_events[0] >= config.burn_in]
    directions = np.sign(config.sigma * (event_states[:, 1] - event_states[:, 0])).astype(np.int8)
    return LorenzSignal(
        config=config,
        time=time,
        states=states,
        sign=_continued_sign(states[:, 0]),
        crossing_times=crossings,
        crossing_directions=directions,
    )


def sign_autocorrelation(sign: np.ndarray, dt: float, max_time: float) -> tuple[np.ndarray, np.ndarray]:
    centered = np.asarray(sign, dtype=float) - float(np.mean(sign))
    n = centered.size
    n_fft = 1 << (2 * n - 1).bit_length()
    spectrum = np.fft.rfft(centered, n=n_fft)
    raw = np.fft.irfft(spectrum * np.conjugate(spectrum), n=n_fft)[:n]
    raw /= np.arange(n, 0, -1)
    if raw[0] <= 1.0e-15:
        corr = np.ones(1)
        return np.zeros(1), corr
    corr = raw / raw[0]
    count = min(corr.size, int(max_time / dt) + 1)
    return np.arange(count) * dt, corr[:count]


def integral_correlation_time(lag: np.ndarray, corr: np.ndarray) -> float:
    if corr.size < 2:
        return 0.0
    nonpositive = np.flatnonzero(corr[1:] <= 0.0)
    stop = int(nonpositive[0] + 2) if nonpositive.size else corr.size
    return float(np.trapezoid(corr[:stop], lag[:stop]))


def _lag_one_correlation(values: np.ndarray) -> float | None:
    if values.size < 3 or np.std(values[:-1]) == 0.0 or np.std(values[1:]) == 0.0:
        return None
    return float(np.corrcoef(values[:-1], values[1:])[0, 1])


def classify_attractor(signal: LorenzSignal) -> str:
    """Conservative finite-record classification; chaotic labels remain candidates until Stage 3."""
    tail = signal.states[-max(100, signal.states.shape[0] // 2) :]
    spread = float(np.max(np.std(tail, axis=0)))
    if spread < 1.0e-7:
        return "fixed"
    runs = np.diff(signal.crossing_times)
    if runs.size < 3:
        return "nonreversing"
    if runs.size >= 8 and np.mean(runs) > 0.0:
        run_cv = float(np.std(runs, ddof=1) / np.mean(runs))
        lag, corr = sign_autocorrelation(signal.sign, signal.dt, min(100.0, signal.config.duration))
        peaks, properties = find_peaks(corr[1:], height=0.8)
        if run_cv < 0.03 and peaks.size >= 2 and properties["peak_heights"][0] > 0.9:
            return "periodic_candidate"
    return "chaotic_candidate"


def screen_multistability(
    sigma: float,
    *,
    dt: float,
    burn_in: float = 80.0,
    duration: float = 60.0,
) -> dict[str, Any]:
    """Compare several basins without claiming a proof of global uniqueness."""
    initials = ((1.0, 1.0, 1.0), (-7.0, 8.0, 20.0), (12.0, -5.0, 30.0))
    rows: list[dict[str, Any]] = []
    for initial in initials:
        sig = simulate_lorenz(
            SignalConfig(
                sigma=sigma,
                burn_in=burn_in,
                duration=duration,
                future_horizon=0.0,
                dt=dt,
                initial=initial,
            )
        )
        summary = sig.summary(max_correlation_time=min(20.0, duration / 2.0))
        rows.append(
            {
                "initial": list(initial),
                "class": summary["attractor_class"],
                "gamma_eff": summary["gamma_eff"],
                "mean_sign": summary["mean_sign"],
            }
        )
    classes = {row["class"] for row in rows}
    gammas = [row["gamma_eff"] for row in rows if row["gamma_eff"] is not None]
    rate_spread = (
        (max(gammas) - min(gammas)) / max(float(np.mean(gammas)), 1.0e-15)
        if len(gammas) > 1
        else 0.0
    )
    return {
        "classification": "multistable_candidate" if len(classes) > 1 else rows[0]["class"],
        "relative_gamma_spread": float(rate_spread),
        "basin_screen": rows,
    }

