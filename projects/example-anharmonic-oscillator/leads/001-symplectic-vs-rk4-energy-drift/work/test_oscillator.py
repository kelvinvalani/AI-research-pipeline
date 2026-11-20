"""Unit tests for Lead 001 (quartic oscillator integrators)."""

from __future__ import annotations

import numpy as np

from work.simulate import force, hamiltonian, integrate_rk4, integrate_verlet


def test_equilibrium_fixed_point() -> None:
    _, q_v, p_v = integrate_verlet(0.0, 0.0, omega=1.0, lam=1.0, dt=0.1, n_steps=50)
    _, q_r, p_r = integrate_rk4(0.0, 0.0, omega=1.0, lam=1.0, dt=0.1, n_steps=50)
    assert np.allclose(q_v, 0.0) and np.allclose(p_v, 0.0)
    assert np.allclose(q_r, 0.0) and np.allclose(p_r, 0.0)


def test_odd_force_symmetry() -> None:
    for q in (0.3, 1.5, 4.2):
        assert np.isclose(force(-q, 1.3, 0.7), -force(q, 1.3, 0.7))


def test_hamiltonian_nonnegative() -> None:
    assert hamiltonian(0.0, 0.0, 1.0, 1.0) == 0.0
    assert hamiltonian(1.2, -0.8, 1.0, 1.0) > 0.0
