"""Stage 2 alpha-sigma atlas for the harmonic Lorenz active particle."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from rpipe.helpers.io import get_run_dir, get_seed, save_summary
from work.first_passage_statistics import compute_first_passage_statistics
from work.lorenz_signal import SignalConfig, screen_multistability, simulate_lorenz
from work.relaxation_statistics import compute_relaxation_statistics
from work.stationary_statistics import compute_stationary_statistics, locate_shape_boundary


@dataclass(frozen=True)
class SweepConfig:
    profile: str
    sigma_points: int
    alpha_points: int
    burn_in: float
    duration: float
    future_horizon: float
    dt: float
    ensemble_size: int
    relaxation_horizon: float
    first_passage_horizon: float
    basin_screen: bool


def profile_config(profile: str) -> SweepConfig:
    if profile == "prototype":
        return SweepConfig(profile, 5, 7, 45.0, 100.0, 32.0, 0.02, 96, 20.0, 32.0, False)
    if profile == "stage2":
        return SweepConfig(profile, 9, 11, 100.0, 320.0, 80.0, 0.01, 320, 50.0, 80.0, True)
    raise ValueError(f"Unknown profile: {profile}")


def _key(sigma: float, alpha: float | None = None) -> str:
    sigma_text = f"{sigma:.8g}".replace(".", "p")
    if alpha is None:
        return f"s_{sigma_text}"
    alpha_text = f"{alpha:.8g}".replace(".", "p")
    return f"s_{sigma_text}_a_{alpha_text}"


def _json_default(value: Any):
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(f"Not JSON serializable: {type(value)!r}")


def _simulate_signal(sigma: float, config: SweepConfig):
    return simulate_lorenz(
        SignalConfig(
            sigma=sigma,
            burn_in=config.burn_in,
            duration=config.duration,
            future_horizon=config.future_horizon,
            dt=config.dt,
        )
    )


def _adaptive_sigmas(
    ordered: list[tuple[float, dict[str, Any]]], maximum: int = 4
) -> list[float]:
    candidates: list[tuple[float, float]] = []
    for (s0, a), (s1, b) in zip(ordered[:-1], ordered[1:], strict=True):
        class_change = a["attractor_class"] != b["attractor_class"]
        g0, g1 = a["gamma_eff"], b["gamma_eff"]
        rate_jump = (
            abs(g1 - g0) / max(0.5 * (abs(g0) + abs(g1)), 1.0e-12)
            if g0 is not None and g1 is not None
            else float(class_change)
        )
        if class_change or rate_jump > 0.35:
            candidates.append((2.0 if class_change else rate_jump, float(np.sqrt(s0 * s1))))
    return [sigma for _, sigma in sorted(candidates, reverse=True)[:maximum]]


def _save_figures(
    run_dir: Path,
    signal_records: list[dict[str, Any]],
    boundaries: list[dict[str, Any]],
    stationary_records: list[dict[str, Any]],
    relaxation_records: list[dict[str, Any]],
    first_passage_records: list[dict[str, Any]],
) -> list[str]:
    figures: list[str] = []
    sigmas = np.asarray([row["sigma"] for row in signal_records])
    gammas = np.asarray([row["gamma_eff"] if row["gamma_eff"] is not None else np.nan for row in signal_records])
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.plot(sigmas, gammas, "o-", lw=1.4)
    ax.set_xscale("log")
    ax.set_xlabel(r"Lorenz parameter $\sigma$")
    ax.set_ylabel(r"measured reversal rate $\gamma_{\rm eff}$")
    ax.grid(alpha=0.25)
    path = run_dir / "gamma_eff_vs_sigma.png"
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    figures.append(path.name)

    usable = [row for row in boundaries if row["alpha_c"] is not None and row["gamma_eff"] is not None]
    if usable:
        fig, ax = plt.subplots(figsize=(6.4, 4.2))
        xs = np.asarray([row["sigma"] for row in usable])
        measured = np.asarray([row["alpha_c"] for row in usable])
        predicted = np.asarray([0.5 * row["gamma_eff"] for row in usable])
        ax.plot(xs, measured, "o-", label="Lorenz measured")
        ax.plot(xs, predicted, "s--", label=r"RTP $\gamma_{\rm eff}/2$")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel(r"$\sigma$")
        ax.set_ylabel(r"shape boundary $\alpha_c$")
        ax.legend()
        ax.grid(alpha=0.25)
        path = run_dir / "shape_boundary.png"
        fig.tight_layout()
        fig.savefig(path, dpi=180)
        plt.close(fig)
        figures.append(path.name)

    points = [row for row in stationary_records if row["rtp_second_relative_discrepancy"] is not None]
    if points:
        fig, ax = plt.subplots(figsize=(6.5, 4.5))
        scatter = ax.scatter(
            [row["sigma"] for row in points],
            [row["alpha"] for row in points],
            c=[row["rtp_second_relative_discrepancy"] for row in points],
            cmap="coolwarm",
            vmin=-0.5,
            vmax=0.5,
            s=42,
        )
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel(r"$\sigma$")
        ax.set_ylabel(r"$\alpha$")
        fig.colorbar(scatter, ax=ax, label=r"relative error in $\langle y^2\rangle$")
        path = run_dir / "stationary_rtp_discrepancy.png"
        fig.tight_layout()
        fig.savefig(path, dpi=180)
        plt.close(fig)
        figures.append(path.name)

    rate_pairs: list[tuple[float, float, str]] = []
    for row in relaxation_records:
        for label in ("origin", "half_edge"):
            item = row["initial_conditions"][label]
            if (
                item["fitted_rate"] is not None
                and item["rtp_predicted_rate"] is not None
                and item["fit_accepted_preliminary"]
            ):
                rate_pairs.append((item["rtp_predicted_rate"], item["fitted_rate"], f"relax {label}"))
    for row in first_passage_records:
        if row["fitted_tail_rate"] is not None and row["rtp_predicted_tail_rate"] is not None:
            rate_pairs.append((row["rtp_predicted_tail_rate"], row["fitted_tail_rate"], "first passage"))
    if rate_pairs:
        fig, ax = plt.subplots(figsize=(5.2, 5.0))
        styles = {"relax origin": "o", "relax half_edge": "s", "first passage": "^"}
        for label, marker in styles.items():
            selected = [(x, y) for x, y, kind in rate_pairs if kind == label]
            if selected:
                ax.scatter([p[0] for p in selected], [p[1] for p in selected], marker=marker, label=label, alpha=0.75)
        maximum = max(max(x, y) for x, y, _ in rate_pairs)
        ax.plot([0.0, maximum], [0.0, maximum], "k--", lw=1.0)
        ax.set_xlabel("effective-RTP predicted rate")
        ax.set_ylabel("Lorenz-ensemble fitted rate")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.25)
        path = run_dir / "rate_comparison.png"
        fig.tight_layout()
        fig.savefig(path, dpi=180)
        plt.close(fig)
        figures.append(path.name)
    return figures


def run_sweep(config: SweepConfig) -> dict[str, Any]:
    seed = get_seed()
    run_dir = get_run_dir()
    base_sigmas = np.unique(np.concatenate((np.geomspace(1.0, 50.0, config.sigma_points), [10.0])))
    base_alphas = np.geomspace(0.05, 5.0, config.alpha_points)
    signals: dict[float, Any] = {}
    signal_summaries: dict[float, dict[str, Any]] = {}
    for sigma in base_sigmas:
        signal = _simulate_signal(float(sigma), config)
        summary = signal.summary()
        signals[float(sigma)] = signal
        signal_summaries[float(sigma)] = summary
    adaptive = _adaptive_sigmas(sorted(signal_summaries.items()))
    for sigma in adaptive:
        if not any(np.isclose(sigma, value) for value in signals):
            signal = _simulate_signal(float(sigma), config)
            signals[float(sigma)] = signal
            signal_summaries[float(sigma)] = signal.summary()

    if config.basin_screen:
        for sigma in sorted(signals):
            screen = screen_multistability(sigma, dt=2.0 * config.dt)
            signal_summaries[sigma]["basin_screen"] = screen
            if screen["classification"] == "multistable_candidate":
                signal_summaries[sigma]["attractor_class"] = "multistable_candidate"

    signal_arrays: dict[str, np.ndarray] = {}
    for sigma, signal in signals.items():
        key = _key(sigma)
        stride = max(1, int(round(0.05 / config.dt)))
        signal_arrays[f"{key}_time"] = signal.time[::stride]
        signal_arrays[f"{key}_states"] = signal.states[::stride]
        signal_arrays[f"{key}_sign"] = signal.sign[::stride]
        signal_arrays[f"{key}_crossings"] = signal.crossing_times

    stationary_records: list[dict[str, Any]] = []
    relaxation_records: list[dict[str, Any]] = []
    first_passage_records: list[dict[str, Any]] = []
    boundaries: list[dict[str, Any]] = []
    density_arrays: dict[str, np.ndarray] = {}
    dynamics_arrays: dict[str, np.ndarray] = {}
    for sigma_index, sigma in enumerate(sorted(signals)):
        signal = signals[sigma]
        gamma_eff = signal_summaries[sigma]["gamma_eff"]
        by_alpha: dict[float, Any] = {}
        for alpha in base_alphas:
            by_alpha[float(alpha)] = compute_stationary_statistics(
                signal.sign,
                signal.dt,
                float(alpha),
                gamma_eff,
                analysis_duration=config.duration,
            )
        boundary_initial = locate_shape_boundary([result.record for result in by_alpha.values()])
        for candidate in boundary_initial["candidates"][:3]:
            extra_alpha = float(np.sqrt(np.prod(candidate["bracket"])))
            if not any(np.isclose(extra_alpha, value) for value in by_alpha):
                by_alpha[extra_alpha] = compute_stationary_statistics(
                    signal.sign,
                    signal.dt,
                    extra_alpha,
                    gamma_eff,
                    analysis_duration=config.duration,
                )
        boundary = locate_shape_boundary([result.record for result in by_alpha.values()])
        boundaries.append(
            {
                "sigma": sigma,
                "gamma_eff": gamma_eff,
                **boundary,
                "rtp_alpha_c": 0.5 * gamma_eff if gamma_eff is not None else None,
                "rtp_relative_discrepancy": (
                    (boundary["alpha_c"] - 0.5 * gamma_eff) / (0.5 * gamma_eff)
                    if boundary["alpha_c"] is not None and gamma_eff is not None
                    else None
                ),
            }
        )
        usable_sign = signal.sign[: int((config.duration + config.future_horizon) / config.dt) + 1]
        for alpha_index, (alpha, stationary) in enumerate(sorted(by_alpha.items())):
            record = {"sigma": sigma, **stationary.record}
            stationary_records.append(record)
            key = _key(sigma, alpha)
            density_arrays[f"{key}_grid_y"] = stationary.grid_y
            density_arrays[f"{key}_density"] = stationary.density
            density_arrays[f"{key}_density_plus"] = stationary.density_plus
            density_arrays[f"{key}_density_minus"] = stationary.density_minus
            point_seed = seed + 10007 * sigma_index + 101 * alpha_index
            relaxation, relaxation_arrays = compute_relaxation_statistics(
                usable_sign,
                config.dt,
                alpha,
                gamma_eff,
                stationary.sample_y,
                horizon=config.relaxation_horizon,
                ensemble_size=config.ensemble_size,
                rng=np.random.default_rng(point_seed),
            )
            relaxation_records.append({"sigma": sigma, **relaxation})
            first_passage, first_passage_arrays = compute_first_passage_statistics(
                usable_sign,
                config.dt,
                alpha,
                gamma_eff,
                horizon=config.first_passage_horizon,
                ensemble_size=config.ensemble_size,
                rng=np.random.default_rng(point_seed + 1),
            )
            first_passage_records.append({"sigma": sigma, **first_passage})
            for name, array in relaxation_arrays.items():
                dynamics_arrays[f"{key}_relax_{name}"] = array
            for name, array in first_passage_arrays.items():
                dynamics_arrays[f"{key}_fpt_{name}"] = array

    signal_records = [{"sigma": sigma, **signal_summaries[sigma]} for sigma in sorted(signals)]
    atlas = {
        "stage": 2,
        "status": "preliminary_unverified",
        "seed": seed,
        "configuration": asdict(config),
        "model": {"r": 28.0, "b": 8.0 / 3.0, "u": float(3.0 * np.sqrt(3.0))},
        "sigma_grid": sorted(signals),
        "alpha_base_grid": base_alphas.tolist(),
        "adaptive_sigma_points": adaptive,
        "signals": signal_records,
        "stationary": stationary_records,
        "shape_boundaries": boundaries,
        "relaxation": relaxation_records,
        "first_passage": first_passage_records,
    }
    atlas_path = run_dir / "alpha_sigma_atlas.json"
    atlas_path.write_text(json.dumps(atlas, indent=2, default=_json_default) + "\n", encoding="utf-8")
    np.savez_compressed(run_dir / "lorenz_signals.npz", **signal_arrays)
    np.savez_compressed(run_dir / "stationary_densities.npz", **density_arrays)
    np.savez_compressed(run_dir / "dynamics_curves.npz", **dynamics_arrays)
    figures = _save_figures(
        run_dir,
        signal_records,
        boundaries,
        stationary_records,
        relaxation_records,
        first_passage_records,
    )

    stationary_discrepancies = [
        abs(row["rtp_second_relative_discrepancy"])
        for row in stationary_records
        if row["rtp_second_relative_discrepancy"] is not None
    ]
    candidate_failures = []
    for row in stationary_records:
        discrepancy = row["rtp_second_relative_discrepancy"]
        se = row["second_moment_se"]
        predicted = row["rtp_second_moment_y"]
        if discrepancy is None or se is None or predicted is None:
            continue
        z_score = abs(row["second_moment_y"] - predicted) / max(se, 1.0e-15)
        if abs(discrepancy) > 0.10 and z_score > 5.0:
            candidate_failures.append(
                {"sigma": row["sigma"], "alpha": row["alpha"], "relative_error": discrepancy, "z_score": z_score}
            )
    candidate_failures.sort(key=lambda row: abs(row["relative_error"]), reverse=True)
    reversing = [row for row in signal_records if row["gamma_eff"] is not None]
    summary = {
        "stage": 2,
        "status": "complete_preliminary_unverified",
        "seed": seed,
        "profile": config.profile,
        "parameter_ranges": {"sigma": [1.0, 50.0], "alpha": [0.05, 5.0]},
        "counts": {
            "sigma": len(signals),
            "stationary_points": len(stationary_records),
            "relaxation_points": len(relaxation_records),
            "first_passage_points": len(first_passage_records),
            "reversing_sigma": len(reversing),
        },
        "signal_overview": [
            {
                "sigma": row["sigma"],
                "class": row["attractor_class"],
                "gamma_eff": row["gamma_eff"],
                "run_cv": row["run_time_cv"],
                "run_serial_correlation": row["run_serial_correlation_lag1"],
            }
            for row in signal_records
        ],
        "shape_boundaries": boundaries,
        "stationary_rtp_second_moment_absolute_relative_error": {
            "median": float(np.median(stationary_discrepancies)) if stationary_discrepancies else None,
            "maximum": float(np.max(stationary_discrepancies)) if stationary_discrepancies else None,
        },
        "unverified_candidate_collapse_failures": candidate_failures[:12],
        "interpretation_guard": "Stage 2 estimates only; no convergence or falsification claim before Stage 3.",
        "artifacts": [
            atlas_path.name,
            "lorenz_signals.npz",
            "stationary_densities.npz",
            "dynamics_curves.npz",
            *figures,
        ],
    }
    save_summary(summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("prototype", "stage2"), default="stage2")
    args = parser.parse_args()
    summary = run_sweep(profile_config(args.profile))
    print(
        f"Stage 2 {args.profile}: {summary['counts']['sigma']} sigma values, "
        f"{summary['counts']['stationary_points']} alpha-sigma points."
    )


if __name__ == "__main__":
    main()

