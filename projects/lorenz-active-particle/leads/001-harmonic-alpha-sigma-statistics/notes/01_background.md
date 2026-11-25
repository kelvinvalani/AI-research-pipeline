# Background and formulation: harmonic Lorenz active particle

## 1. Conventions

| Item | Convention |
| :--- | :--- |
| Time | Dimensionless Lorenz time |
| Position | One-dimensional, $x\in\mathbb{R}$ |
| Potential | $V(x)=\alpha x^2$, with $\alpha>0$ |
| Restoring rate | $\mu:=2\alpha$ |
| Lorenz parameters | $r=28$, $b=8/3$, $\sigma\in[1,50]$ |
| Propulsion speed | $u=\sqrt{r-1}=3\sqrt{3}$, fixed when $\sigma$ varies |
| Direction process | $s(t):=\operatorname{sgn}X(t)\in\{-1,+1\}$ |
| Probability | Natural invariant Lorenz measure, approximated by post-burn-in phase samples |
| Harmonic support scale | $x_+=u/\mu=u/(2\alpha)$ |

No Fourier convention or metric signature is needed. All numerical outputs will state
the timestep, integration tolerances, burn-in, sampling duration, and ensemble size.

## 2. Reference digest

### Valani and Paganin, *Attractor-driven matter* (Chaos 33, 023125, 2023)

Source: `projects/lorenz-active-particle/refs/attractor-driven-matter-valani-paganin-2023.pdf`.

- Section II, Eq. (2), couples position to the Lorenz variables. The Lorenz equations
  use $\dot X=\sigma(Y-X)$, $\dot Y=-XZ+rX-Y$, and $\dot Z=XY-bZ$.
- Section IV.B.1, Eq. (14), defines the constant-speed one-dimensional coarse graining
  $\dot x=u\operatorname{sgn}X$. Direction changes occur at crossings of the plane $X=0$.
- Figure 3 uses $(\sigma,r,b)=(10,28,8/3)$ and $u=\sqrt{r-1}=3\sqrt3$. Its run-time
  distribution has discrete peaks under an exponentially decaying envelope, already
  showing that the direction process is not a Poisson telegraph process.
- Appendix B states that the paper first integrates the internal chaotic system and
  then couples it to the particle motion. Our implementation will instead resolve
  $X=0$ events accurately and verify timestep independence.

### Dhar et al., *Run-and-tumble particle in one-dimensional confining potentials*

Source: `projects/lorenz-active-particle/refs/run-and-tumble-confining-potentials-dhar-et-al-2019.pdf`.

- Equations (1)-(3) define the stochastic RTP $\dot x=f(x)+v_0\sigma_s(t)$, where
  $\sigma_s=\pm1$ flips at Poisson rate $\gamma$ and
  $\langle v_0\sigma_s(t)v_0\sigma_s(0)\rangle=v_0^2e^{-2\gamma|t|}$.
- Section II, Eq. (20), gives the stationary density for a general confining force.
  For the harmonic force $f=-\mu x$, Eqs. (21)-(22) give
  $$
  P_{\rm RTP}(x)\propto\left[1-\left(\frac{\mu x}{v_0}\right)^2\right]^{\gamma/\mu-1},
  \qquad |x|\le v_0/\mu.
  $$
  The shape changes at $\gamma=\mu$, equivalently $\alpha_c=\gamma/2$.
- Section III obtains the harmonic time-dependent solution in Laplace space. A generic
  initial position relaxes at rate $\mu$; for $x_0=0$, the symmetry-sensitive rate is
  $\min(\mu+2\gamma,2\mu)$.
- Section IV defines survival and first-passage statistics and gives the harmonic
  long-time decay exponent through a hypergeometric root, Eqs. (86)-(90).

## 3. Deterministic model

The agreed harmonic Lorenz active particle is

$$
\dot x=-\mu x+u s(t),\qquad s(t)=\operatorname{sgn}X(t),\qquad \mu=2\alpha,
$$

$$
\dot X=\sigma(Y-X),\qquad
\dot Y=rX-Y-XZ,\qquad
\dot Z=XY-bZ.
$$

We fix $r=28$, $b=8/3$, and $u=3\sqrt3$, then sweep
$\sigma\in[1,50]$ and $\alpha\in[0.05,5]$ on logarithmic grids with adaptive
refinement near dynamical and statistical transitions.

For any measurable $s(t)\in\{-1,+1\}$, variation of constants gives

$$
x(t)=e^{-\mu t}x(0)+u\int_0^t e^{-\mu(t-q)}s(q)\,dq.
$$

Therefore

$$
|x(t)|\le e^{-\mu t}|x(0)|+\frac{u}{\mu}(1-e^{-\mu t}),
$$

and $[-u/\mu,u/\mu]$ is forward invariant and globally absorbing. This support
bound is exact and does not require Poisson reversals.

## 4. Statistical definitions

After a Lorenz burn-in, let $t_n$ be successive transversal $X=0$ crossings and
$\tau_n=t_{n+1}-t_n$. When reversals persist,

$$
\gamma_{\rm eff}(\sigma):=\frac{1}{\langle\tau_n\rangle}.
$$

The complete empirical law of $\tau_n$, its serial correlations, and

$$
C_s(t)=\langle s(t_0+t)s(t_0)\rangle
$$

will also be measured. The primary comparison conjecture substitutes
$\gamma\mapsto\gamma_{\rm eff}$ in the RTP formulas. Because the Lorenz reversal
process has memory, this substitution is an approximation to be tested, not assumed.

Stationary statistics include $P(x)$, $P_\pm(x)$, moments, edge behavior, and modality.
Relaxation statistics include $P(x,t)$ and moment/distributional decay from $x_0=0$
and $x_0=x_+/2$. First-passage statistics use $x_0=x_+/2$, an absorbing origin,
and both initial direction sectors sampled from the invariant Lorenz ensemble.

## 5. Verification plan and failure modes

- Refine ODE tolerances and maximum step size until crossing times and low-order moments
  change by less than 2%.
- Refine burn-in, trajectory duration, independent phase spacing, and ensemble size.
- Verify Lorenz symmetry under $(X,Y)\mapsto(-X,-Y)$ and stationary particle symmetry
  $P(x)=P(-x)$ when the invariant measure is sampled symmetrically.
- Verify the exact support $|x|\le u/\mu$ after transients and the convolution solution
  against direct particle integration.
- Verify relaxation and first-passage exponents to 5% under refinement; inspect local
  slopes and competing tail forms before claiming exponential decay.
- Classify fixed, periodic, chaotic, multistable, or nonmixing Lorenz behavior before
  interpreting $\gamma_{\rm eff}$ or ergodic averages.
- Treat finite-time correlations, rare long runs, density-estimator edge bias, unresolved
  zero crossings, and censoring of first-passage tails as explicit failure modes.
- Falsify the effective-RTP collapse only when a discrepancy exceeds 10% and five
  estimated standard errors after the numerical convergence gates pass.

## 6. Stage 2 execution plan

1. Generate and classify converged Lorenz direction signals across $\sigma$.
2. Measure reversal, correlation, and free-propulsion diagnostics.
3. Use the exact linear filter for $x(t)$ to compute stationary statistics across
   $(\alpha,\sigma)$ and locate the modality boundary.
4. Compute ensemble relaxation from the two agreed initial positions.
5. Compute censored survival and first-passage statistics from $x_+/2$.
6. Compare each observable with the harmonic RTP prediction using $\gamma_{\rm eff}$.
7. Run all Stage 3 convergence, symmetry, support, and cross-method checks before
   interpreting the phase diagram.
