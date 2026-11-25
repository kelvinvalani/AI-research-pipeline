"""Stationary harmonic-particle densities, moments, edge behavior, and modality."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.stats import gaussian_kde

from rpipe.helpers.io import get_seed, save_summary
from work.harmonic_particle import normalized_filter, rtp_density_y, rtp_moments_y
from work.lorenz_signal import SignalConfig, simulate_lorenz


@dataclass
class StationaryResult:
    record: dict[str, Any]
    sample_y: np.ndarray
    grid_y: np.ndarray
    density: np.ndarray
    density_plus: np.ndarray
    density_minus: np.ndarray


def _block_standard_error(values: np.ndarray, transform, n_blocks: int = 24) -> float | None:
    blocks = [block for block in np.array_split(values, n_blocks) if block.size]
    estimates = np.asarray([transform(block) for block in blocks], dtype=float)
    if estimates.size < 2:
        return None
    return float(np.std(estimates, ddof=1) / np.sqrt(estimates.size))


def _safe_kde(sample: np.ndarray, grid: np.ndarray) -> np.ndarray:
    if sample.size == 0:
        return np.zeros_like(grid)
    if sample.size < 8 or np.std(sample) < 1.0e-10:
        out = np.zeros_like(grid)
        out[np.argmin(np.abs(grid - float(np.mean(sample))))] = 1.0 / (grid[1] - grid[0])
        return out
    reduced = sample[:: max(1, sample.size // 12000)]
    return gaussian_kde(reduced)(grid)


def _density_on_grid(sample: np.ndarray, grid: np.ndarray, *, symmetrize: bool) -> np.ndarray:
    data = np.concatenate((sample, -sample)) if symmetrize else sample
    density = _safe_kde(data, grid)
    norm = float(np.trapezoid(density, grid))
    return density / norm if norm > 0.0 else density


def compute_stationary_statistics(
    sign: np.ndarray,
    dt: float,
    alpha: float,
    gamma_eff: float | None,
    *,
    analysis_duration: float,
) -> StationaryResult:
    mu = 2.0 * alpha
    count = min(sign.size, int(analysis_duration / dt) + 1)
    y = normalized_filter(sign[:count], mu, dt)
    discard_time = min(max(20.0, 10.0 / mu), 0.55 * analysis_duration)
    discard = min(int(discard_time / dt), max(0, y.size - 32))
    sample = y[discard:]
    sign_sample = sign[discard : discard + sample.size]
    grid = np.linspace(-0.995, 0.995, 401)
    density_raw = _density_on_grid(sample, grid, symmetrize=False)
    density = _density_on_grid(sample, grid, symmetrize=True)
    plus = _density_on_grid(sample[sign_sample > 0], grid, symmetrize=False)
    minus = _density_on_grid(sample[sign_sample < 0], grid, symmetrize=False)

    center_idx = int(np.argmin(np.abs(grid)))
    shoulder = 0.20
    left_idx = int(np.argmin(np.abs(grid + shoulder)))
    right_idx = int(np.argmin(np.abs(grid - shoulder)))
    p_center = float(density[center_idx])
    p_shoulder = float(0.5 * (density[left_idx] + density[right_idx]))
    shape_score = (p_shoulder - p_center) / max(p_center, 1.0e-12)
    if shape_score > 0.025:
        modality = "edge_peaked"
    elif shape_score < -0.025:
        modality = "center_peaked"
    else:
        modality = "flat_or_transition"

    edge_mask = (np.abs(grid) >= 0.72) & (np.abs(grid) <= 0.94) & (density > 1.0e-12)
    if np.count_nonzero(edge_mask) >= 8:
        edge_exponent = float(
            np.polyfit(np.log(1.0 - grid[edge_mask] ** 2), np.log(density[edge_mask]), 1)[0]
        )
    else:
        edge_exponent = None

    second = float(np.mean(sample**2))
    fourth = float(np.mean(sample**4))
    symmetry_error = float(np.trapezoid(np.abs(density_raw - density_raw[::-1]), grid) / 2.0)
    rtp = rtp_moments_y(mu, gamma_eff) if gamma_eff is not None else None
    if gamma_eff is not None:
        rtp_density = rtp_density_y(grid, mu, gamma_eff)
        rtp_density /= float(np.trapezoid(rtp_density, grid))
        density_l1 = float(np.trapezoid(np.abs(density - rtp_density), grid))
        second_discrepancy = (second - rtp["second"]) / rtp["second"]
        fourth_discrepancy = (fourth - rtp["fourth"]) / rtp["fourth"]
        rtp_edge_exponent = gamma_eff / mu - 1.0
    else:
        density_l1 = second_discrepancy = fourth_discrepancy = rtp_edge_exponent = None

    record = {
        "alpha": float(alpha),
        "mu": float(mu),
        "x_plus": float(3.0 * np.sqrt(3.0) / mu),
        "discard_time": float(discard_time),
        "n_stationary_samples": int(sample.size),
        "mean_y": float(np.mean(sample)),
        "second_moment_y": second,
        "fourth_moment_y": fourth,
        "second_moment_se": _block_standard_error(sample, lambda block: np.mean(block**2)),
        "fourth_moment_se": _block_standard_error(sample, lambda block: np.mean(block**4)),
        "conditional_mean_y_plus": (
            float(np.mean(sample[sign_sample > 0])) if np.any(sign_sample > 0) else None
        ),
        "conditional_mean_y_minus": (
            float(np.mean(sample[sign_sample < 0])) if np.any(sign_sample < 0) else None
        ),
        "support_excess": float(max(0.0, np.max(np.abs(sample)) - 1.0)),
        "symmetry_l1": symmetry_error,
        "modality": modality,
        "shape_score": float(shape_score),
        "edge_exponent": edge_exponent,
        "rtp_edge_exponent": rtp_edge_exponent,
        "rtp_second_moment_y": rtp["second"] if rtp else None,
        "rtp_fourth_moment_y": rtp["fourth"] if rtp else None,
        "rtp_second_relative_discrepancy": second_discrepancy,
        "rtp_fourth_relative_discrepancy": fourth_discrepancy,
        "rtp_density_l1": density_l1,
    }
    return StationaryResult(record, sample, grid, density, plus, minus)


def locate_shape_boundary(records: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(records, key=lambda row: row["alpha"])
    candidates: list[dict[str, Any]] = []
    for left, right in zip(ordered[:-1], ordered[1:], strict=True):
        s0, s1 = float(left["shape_score"]), float(right["shape_score"])
        if s0 == 0.0 or s0 * s1 < 0.0:
            log_a0, log_a1 = np.log(left["alpha"]), np.log(right["alpha"])
            fraction = -s0 / (s1 - s0) if s1 != s0 else 0.5
            estimate = float(np.exp(log_a0 + fraction * (log_a1 - log_a0)))
            candidates.append(
                {"alpha_c": estimate, "bracket": [left["alpha"], right["alpha"]]}
            )
    if not candidates:
        return {
            "alpha_c": None,
            "bracket": None,
            "n_crossings": 0,
            "ambiguous": False,
            "candidates": [],
        }
    if len(candidates) == 1:
        return {
            **candidates[0],
            "n_crossings": 1,
            "ambiguous": False,
            "candidates": candidates,
        }
    return {
        "alpha_c": None,
        "bracket": None,
        "n_crossings": len(candidates),
        "ambiguous": True,
        "candidates": candidates,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sigma", type=float, default=10.0)
    parser.add_argument("--alpha", type=float, default=1.0)
    parser.add_argument("--duration", type=float, default=180.0)
    parser.add_argument("--dt", type=float, default=0.02)
    args = parser.parse_args()
    signal = simulate_lorenz(
        SignalConfig(args.sigma, burn_in=80.0, duration=args.duration, future_horizon=0.0, dt=args.dt)
    )
    signal_summary = signal.summary()
    result = compute_stationary_statistics(
        signal.sign,
        signal.dt,
        args.alpha,
        signal_summary["gamma_eff"],
        analysis_duration=args.duration,
    )
    save_summary(
        {"stage": 2, "seed": get_seed(), "signal": signal_summary, "stationary": result.record}
    )


if __name__ == "__main__":
    main()

