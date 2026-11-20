# Background Research & Mathematical Formulation — Symplectic Verlet vs. RK4

## 1. Motivation & Context

Standard high-order explicit Runge-Kutta schemes (like RK4) achieve small local truncation error $O(h^5)$ per step, yet they do not preserve the canonical symplectic 2-form $dq \wedge dp$. Over long integration horizons, this manifests as secular energy drift. Symplectic integrators such as 2nd-order Velocity Verlet preserve a nearby modified ("shadow") Hamiltonian $\tilde{H} = H + h^2 H_2 + \cdots$, keeping the true energy error bounded over exponentially long times.

## 2. Notation & Conventions

| Symbol | Meaning | Domain |
| :--- | :--- | :--- |
| $q(t), p(t)$ | Generalized position & momentum (mass $m = 1$) | $\mathbb{R}$ |
| $\omega$ | Linear angular frequency | $\omega > 0$ |
| $\lambda$ | Quartic anharmonic coupling | $\lambda \ge 0$ |
| $h$ | Uniform integration timestep | $h > 0$ |

## 3. Governing Equations

$$
H(q, p) = \frac{1}{2} p^2 + \frac{1}{2}\omega^2 q^2 + \frac{1}{4}\lambda q^4
$$

$$
\dot{q} = \frac{\partial H}{\partial p} = p, \qquad
\dot{p} = -\frac{\partial H}{\partial q} = -\omega^2 q - \lambda q^3.
$$

Exact time derivative along any trajectory:

$$
\frac{dH}{dt} = \frac{\partial H}{\partial q}\dot{q} + \frac{\partial H}{\partial p}\dot{p} = (\omega^2 q + \lambda q^3)p + p(-\omega^2 q - \lambda q^3) = 0.
$$

## 4. Analytic Limiting Cases & Verification Targets

1. **Harmonic limit ($\lambda = 0$)**: Exact solution for $(q_0, p_0) = (q_0, 0)$ is $q(t) = q_0 \cos(\omega t)$, $p(t) = -q_0 \omega \sin(\omega t)$.
2. **Convergence orders**: Velocity Verlet must converge at order $p = 2$, RK4 at order $p = 4$ as $h \to 0$.
3. **Time-reversal symmetry**: Velocity Verlet is time-reversible; integrating forward by $N$ steps and flipping $p \to -p$ then integrating $N$ steps must recover $(q_0, -p_0)$ to machine precision.
