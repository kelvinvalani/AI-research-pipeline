# Analytic derivations and estimator definitions

## 1. Conventions and dimensionless variables

| Item | Convention |
| :--- | :--- |
| Time | Lorenz time; all rates have units of inverse Lorenz time |
| Harmonic rate | $\mu=2\alpha>0$ |
| Propulsion | $u=3\sqrt3$ |
| Harmonic edge | $x_+=u/\mu$ |
| Normalized position | $y=x/x_+=\mu x/u\in[-1,1]$ after absorption into the trap |
| Direction | $s(t)=\operatorname{sgn}X(t)\in\{-1,+1\}$, continued through isolated zeros |
| Ensemble | Uniform post-burn-in phases of one long Lorenz trajectory, stratified by sign where required |

The numerical implementation uses the agreed equations without rescaling Lorenz time or
changing the Lorenz parameters. Normalizing particle position is only a conditioning device:

$$
\dot y=\mu[s(t)-y].
$$

## 2. Exact particle propagator and support

Variation of constants gives

$$
x(t+h)=e^{-\mu h}x(t)+u\int_t^{t+h}e^{-\mu(t+h-q)}s(q)\,dq.
$$

If $s$ is constant on the interval, this becomes the exact update

$$
y(t+h)=e^{-\mu h}y(t)+(1-e^{-\mu h})s.
$$

Lorenz $X=0$ crossings are resolved as adaptive ODE events. The Stage 2 particle estimator
holds the measured sign constant over each uniform output interval and applies this exact
update. Its remaining error is therefore crossing alignment within one output interval; the
declared Stage 3 timestep refinement measures that error. For arbitrary measurable $s$,

$$
|x(t)|\le e^{-\mu t}|x(0)|+x_+(1-e^{-\mu t}),
$$

which proves that $[-x_+,x_+]$ is forward invariant and globally absorbing.

## 3. Harmonic RTP benchmark

With a Poisson reversal rate $\gamma$, the normalized stationary density is

$$
p_{\rm RTP}(y)=\frac{(1-y^2)^{a-1}}{B(1/2,a)},\qquad
a=\frac{\gamma}{\mu},\qquad |y|<1.
$$

The beta integral gives

$$
\langle y^2\rangle_{\rm RTP}=\frac{1}{2a+1}
=\frac{\mu}{\mu+2\gamma},
$$

and

$$
\langle y^4\rangle_{\rm RTP}
=\frac{3}{(2a+1)(2a+3)}
=\frac{3\mu^2}{(\mu+2\gamma)(3\mu+2\gamma)}.
$$

The density is edge divergent for $a<1$, uniform at $a=1$, and center peaked for
$a>1$. Therefore the RTP comparison predicts $\mu=\gamma$, or
$\alpha_c=\gamma/2$. The implementation evaluates the beta normalization and moments
independently and includes symbolic-numeric spot checks in `verify_statistics.py`.

## 4. Relaxation observables

For the deterministic Lorenz ensemble, no Markov closure is imposed. At each sampled
post-burn-in phase, the exact particle propagator is driven by the subsequent Lorenz sign
history. We record densities, moments, and the one-dimensional Wasserstein distance to the
stationary empirical sample.

For $x_0=x_+/2$, the primary fitted observable is
$|\langle y(t)\rangle-\langle y\rangle_{\rm st}|$. Its effective-RTP comparison rate is
$\mu$. For $x_0=0$, symmetry suppresses that mode, so the fitted observable is
$|\langle y^2(t)\rangle-\langle y^2\rangle_{\rm st}|$, compared with

$$
\lambda_{0,\rm RTP}=\min(\mu+2\gamma,2\mu).
$$

Every exponential fit reports its window and $R^2$; a poor or unstable fit is retained as
evidence against a single exponential rather than silently discarded.

## 5. First-passage benchmark

The first-passage experiment starts at $y_0=1/2$ and stops at the first crossing of
$y=0$. Post-burn-in Lorenz phases are separated into $s(0)=+1$ and $s(0)=-1$ sectors.
The sector survival curves are $Q_+(t)$ and $Q_-(t)$, and the agreed symmetric average is

$$
Q(t)=\frac{Q_+(t)+Q_-(t)}{2}.
$$

For the harmonic RTP, Dhar et al. Eqs. (86)--(90) give
$Q(t)\sim e^{-\theta t}$, where $\theta$ is the lowest positive root of

$$
{}_2F_1\!\left(-\frac{\theta}{\mu},
\frac{2\gamma-\theta}{\mu};
\frac{\gamma-\theta}{\mu};\frac12\right)=0.
$$

The numerical root search is restricted to the physical lowest branch and checked against
$\theta\to\gamma$ for $\gamma/\mu\to0$ and $\theta\to\mu$ for
$\gamma/\mu\to\infty$. Censored trajectories contribute to survival and the restricted
mean $\int_0^{t_{\max}}Q(t)\,dt$; an ordinary mean is reported only when censoring is zero.

## 6. Numerical assumptions used only for Stage 2 execution

- Lorenz trajectories are integrated with adaptive DOP853, tight relative/absolute
  tolerances, and a maximum step tied to the output interval.
- Crossing times are found by integrating with the terminal-free event $X=0$; particle
  updates use the sign on the uniform output grid and must pass the declared timestep
  refinement before their rates or moments are treated as converged.
- Stationary estimates discard at least ten particle relaxation times when the available
  record permits it.
- Long-time phases are sampled uniformly from the available invariant-measure record.
- Density modality is measured by a symmetric KDE center-contrast score and accompanied
  by the raw score; the classification remains preliminary until Stage 3 estimator and
  sample-size refinement.
- Rate fits use explicit survival/observable windows and local-slope diagnostics. Stage 2
  values are descriptive and cannot satisfy the declared convergence gates until Stage 3.

