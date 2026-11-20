# Background Research & Mathematical Formulation — Global Lyapunov Stability

## 1. Motivation & Context

Following Lead 001's numerical dynamics study, we want machine-checked guarantees (not just numerical samples) that the origin $(0, 0)$ is globally Lyapunov-stable for every $\omega > 0, \lambda > 0$, with explicit closed-form bounds on $(q, p)$ in terms of the initial energy $E_0 = H(q_0, p_0)$.

## 2. Theorem Statement

Let $\omega > 0, \lambda > 0$, and $H(q, p) = \frac{1}{2} p^2 + \frac{1}{2}\omega^2 q^2 + \frac{1}{4}\lambda q^4$. Then:
1. $H(0, 0) = 0$, and for all $(q, p) \neq (0, 0)$, $H(q, p) > 0$.
2. Along any solution of $\dot{q} = p,\ \dot{p} = -\omega^2 q - \lambda q^3$, $\frac{d}{dt} H(q(t), p(t)) = 0$.
3. Whenever $H(q, p) \le E_0$, we have $p^2 \le 2 E_0$ and $\omega^2 q^2 \le 2 E_0$.

## 3. Negative Control (Falsification Boundary)

If $\lambda < 0$ (softening / inverted quartic potential), the quartic term dominates at large $|q|$, so $H(q, p)$ is unbounded below and strict positivity fails. Testing that Z3 constructs an explicit witness with $\lambda < 0$ and $H(q, p) < 0$ validates that our SMT encoding is not vacuously unsat.
