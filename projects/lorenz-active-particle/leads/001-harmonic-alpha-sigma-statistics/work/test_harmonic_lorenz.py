"""Unit and invariant tests registered for the lead's Stage 3 verification gate."""

from __future__ import annotations

import numpy as np
from scipy.integrate import quad

from work.harmonic_particle import (
    natural_phase_indices,
    normalized_filter,
    rtp_density_y,
    rtp_first_passage_rate,
    rtp_moments_y,
)
from work.lorenz_signal import lorenz_rhs
from work.first_passage_statistics import compute_first_passage_statistics
from work.relaxation_statistics import compute_relaxation_statistics


def test_lorenz_xy_inversion_symmetry() -> None:
    state = np.asarray((3.2, -5.1, 19.0))
    transformed = state.copy()
    transformed[:2] *= -1.0
    rhs = np.asarray(lorenz_rhs(0.0, state, 10.0))
    transformed_rhs = np.asarray(lorenz_rhs(0.0, transformed, 10.0))
    expected = rhs.copy()
    expected[:2] *= -1.0
    np.testing.assert_allclose(transformed_rhs, expected, rtol=1.0e-14, atol=1.0e-14)


def test_constant_sign_filter_is_exact() -> None:
    mu, dt, y0 = 1.7, 0.01, -0.4
    sign = np.ones(1001, dtype=np.int8)
    actual = normalized_filter(sign, mu, dt, y0)
    time = np.arange(sign.size) * dt
    expected = 1.0 + (y0 - 1.0) * np.exp(-mu * time)
    np.testing.assert_allclose(actual, expected, rtol=5.0e-14, atol=5.0e-14)


def test_filter_preserves_normalized_support() -> None:
    rng = np.random.default_rng(17)
    sign = rng.choice((-1, 1), size=50000)
    actual = normalized_filter(sign, 0.1, 0.01, 0.5)
    assert np.max(np.abs(actual)) <= 1.0 + 1.0e-14


def test_rtp_density_and_moments() -> None:
    mu, gamma = 0.8, 1.3
    norm = quad(lambda y: float(rtp_density_y(np.asarray([y]), mu, gamma)[0]), -1.0, 1.0)[0]
    second = quad(lambda y: y * y * float(rtp_density_y(np.asarray([y]), mu, gamma)[0]), -1.0, 1.0)[0]
    fourth = quad(lambda y: y**4 * float(rtp_density_y(np.asarray([y]), mu, gamma)[0]), -1.0, 1.0)[0]
    formulas = rtp_moments_y(mu, gamma)
    assert abs(norm - 1.0) < 2.0e-10
    assert abs(second - formulas["second"]) < 2.0e-10
    assert abs(fourth - formulas["fourth"]) < 2.0e-10


def test_natural_phase_samples_have_complete_future() -> None:
    indices = natural_phase_indices(1000, 200, 128, np.random.default_rng(42))
    assert indices.size == 128
    assert np.unique(indices).size == indices.size
    assert indices.min() >= 0
    assert indices.max() + 200 < 1000


def test_rtp_first_passage_root_is_physical() -> None:
    for gamma in (0.1, 0.5, 1.0, 5.0):
        theta = rtp_first_passage_rate(1.0, gamma)
        assert theta is not None
        assert 0.0 < theta <= 1.0


def test_rtp_first_passage_asymptotic_limits() -> None:
    theta_small = rtp_first_passage_rate(1.0, 0.02)
    theta_large = rtp_first_passage_rate(1.0, 200.0)
    assert theta_small is not None
    assert theta_large is not None
    assert abs(theta_small - 0.02) / 0.02 < 0.12
    assert abs(theta_large - 1.0) < 0.06


def test_explicit_phase_indices_are_respected() -> None:
    sign = np.tile(np.asarray((1, 1, -1, -1), dtype=np.int8), 1000)
    phases = np.asarray((10, 100, 500), dtype=int)
    stationary = np.linspace(-0.5, 0.5, 101)
    relaxation, _ = compute_relaxation_statistics(
        sign,
        0.01,
        1.0,
        0.5,
        stationary,
        horizon=1.0,
        ensemble_size=999,
        rng=np.random.default_rng(1),
        phase_indices=phases,
    )
    passage, _ = compute_first_passage_statistics(
        sign,
        0.01,
        1.0,
        0.5,
        horizon=1.0,
        ensemble_size=999,
        rng=np.random.default_rng(1),
        phase_indices=phases,
    )
    assert relaxation["ensemble_size"] == phases.size
    assert sum(row["ensemble_size"] for row in passage["sectors"].values()) == phases.size

