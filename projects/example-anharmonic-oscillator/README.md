# Quartic Anharmonic Oscillator — Dynamics & Stability

> Reference project demonstrating the 4-stage research pipeline (`idea -> research -> compute/prove -> verify -> evaluate`) across numerical physics, symbolic algebra, Z3/SMT, and Lean 4.

## Core Research Questions

1. How does long-time energy conservation compare between a 2nd-order symplectic integrator (Velocity Verlet) and a higher-order non-symplectic integrator (RK4) for the quartic oscillator?
2. Can we machine-verify global Lyapunov stability and exact phase-space amplitude bounds for all $\omega > 0, \lambda > 0$?

## Lead Index

| Lead ID | Title | Kind | Status | Verdict Summary |
| :--- | :--- | :--- | :--- | :--- |
| `001-symplectic-vs-rk4-energy-drift` | Symplectic Verlet vs. RK4 Long-Time Energy Drift | hybrid | `confirmed` | Verlet maintains bounded $O(h^2)$ energy oscillation with zero secular drift over $T=500$, while RK4 drifts monotonically. |
| `002-lyapunov-stability-bound` | Global Lyapunov Positivity & Phase-Space Bounds | formal | `confirmed` | SymPy + Z3 prove $\dot{H}=0$, strict positivity, and exact $|q|,|p|$ bounds (`unsat` negated goal; $\lambda<0$ counterexample verified); Lean 4 theorem passes static audit. |

## Notes & Promoted Primitives

- Both leads are self-contained reference examples; no domain-specific oscillator code has been promoted to `src/rpipe/shared/` yet.
