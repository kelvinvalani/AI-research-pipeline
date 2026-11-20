"""Numerical comparison of Velocity Verlet (symplectic) vs RK4 on the quartic oscillator."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from rpipe.helpers.io import get_run_dir, save_summary


def hamiltonian(q: np.ndarray | float, p: np.ndarray | float, omega: float, lam: float):
    return 0.5 * p**2 + 0.5 * (omega**2) * q**2 + 0.25 * lam * q**4


def force(q: float, omega: float, lam: float) -> float:
    return -(omega**2) * q - lam * (q**3)


def integrate_verlet(
    q0: float, p0: float, *, omega: float, lam: float, dt: float, n_steps: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    t = np.arange(n_steps + 1, dtype=np.float64) * dt
    q = np.empty(n_steps + 1, dtype=np.float64)
    p = np.empty(n_steps + 1, dtype=np.float64)
    q[0], p[0] = q0, p0
    a = force(q0, omega, lam)
    for i in range(n_steps):
        p_half = p[i] + 0.5 * dt * a
        q_next = q[i] + dt * p_half
        a_next = force(q_next, omega, lam)
        p_next = p_half + 0.5 * dt * a_next
        q[i + 1], p[i + 1] = q_next, p_next
        a = a_next
    return t, q, p


def integrate_rk4(
    q0: float, p0: float, *, omega: float, lam: float, dt: float, n_steps: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    t = np.arange(n_steps + 1, dtype=np.float64) * dt
    q = np.empty(n_steps + 1, dtype=np.float64)
    p = np.empty(n_steps + 1, dtype=np.float64)
    q[0], p[0] = q0, p0
    for i in range(n_steps):
        qi, pi = q[i], p[i]
        k1_q, k1_p = pi, force(qi, omega, lam)
        k2_q, k2_p = pi + 0.5 * dt * k1_p, force(qi + 0.5 * dt * k1_q, omega, lam)
        k3_q, k3_p = pi + 0.5 * dt * k2_p, force(qi + 0.5 * dt * k2_q, omega, lam)
        k4_q, k4_p = pi + dt * k3_p, force(qi + dt * k3_q, omega, lam)
        q[i + 1] = qi + (dt / 6.0) * (k1_q + 2.0 * k2_q + 2.0 * k3_q + k4_q)
        p[i + 1] = pi + (dt / 6.0) * (k1_p + 2.0 * k2_p + 2.0 * k3_p + k4_p)
    return t, q, p


def main() -> None:
    omega = 1.0
    lam = 1.0
    q0, p0 = 1.5, 0.0
    dt = 0.25
    t_max = 500.0
    n_steps = int(round(t_max / dt))

    t, q_v, p_v = integrate_verlet(q0, p0, omega=omega, lam=lam, dt=dt, n_steps=n_steps)
    _, q_r, p_r = integrate_rk4(q0, p0, omega=omega, lam=lam, dt=dt, n_steps=n_steps)

    e0 = float(hamiltonian(q0, p0, omega, lam))
    err_v = np.abs(hamiltonian(q_v, p_v, omega, lam) - e0)
    err_r = np.abs(hamiltonian(q_r, p_r, omega, lam) - e0)

    early_slice = slice(0, n_steps // 10)
    late_slice = slice(9 * n_steps // 10, n_steps + 1)

    verlet_early_max = float(np.max(err_v[early_slice]))
    verlet_late_max = float(np.max(err_v[late_slice]))
    verlet_overall_max = float(np.max(err_v))
    rk4_final_err = float(err_r[-1])
    rk4_overall_max = float(np.max(err_r))

    run_dir = get_run_dir()
    fig_path = run_dir / "energy_drift.png"
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    ax.plot(t, err_v, label="Velocity Verlet (2nd-order symplectic)", lw=1.0)
    ax.plot(t, err_r, label="RK4 (4th-order non-symplectic)", lw=1.5)
    ax.set_xlabel("Dimensionless time $t$")
    ax.set_ylabel(r"$|H(t) - H(0)|$")
    ax.set_title(rf"Quartic Oscillator Energy Error ($\omega={omega}, \lambda={lam}, h={dt}$)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(fig_path)
    plt.close(fig)

    summary = {
        "parameters": {"omega": omega, "lambda": lam, "q0": q0, "p0": p0, "dt": dt, "T": t_max},
        "initial_energy": round(e0, 8),
        "verlet_early_max_err": round(verlet_early_max, 8),
        "verlet_late_max_err": round(verlet_late_max, 8),
        "verlet_late_to_early_ratio": round(verlet_late_max / verlet_early_max, 4),
        "verlet_overall_max_err": round(verlet_overall_max, 8),
        "rk4_final_err": round(rk4_final_err, 8),
        "rk4_overall_max_err": round(rk4_overall_max, 8),
        "rk4_to_verlet_final_ratio": round(rk4_final_err / verlet_overall_max, 4),
        "figure": fig_path.name,
    }
    save_summary(summary, run_dir=run_dir)
    print(f"Saved simulation summary & figure to {run_dir}")


if __name__ == "__main__":
    main()
