---
name: craft-numerical-simulation
description: >-
  Craft skill for rigorous numerical physics and mathematics simulations in Python
  (NumPy, SciPy, Matplotlib, optional JAX): nondimensionalization, integrator choice,
  conditioning, convergence testing, parameter sweeps, and publication-grade figures.
---

# Craft: Numerical Simulation & Scientific Computing

Load this skill when writing or debugging numerical simulations, ODE/PDE solvers, Monte Carlo samplers, eigensolvers, or parameter sweeps in `work/`.

## Engineering & Physics Discipline

1. **Nondimensionalize Before Coding**
   Scale coordinates, time, and fields so $O(1)$ quantities are simulated. Avoid multiplying $10^{-34}$ by $10^{23}$ in raw float64 when dimensionless equations reveal the true control parameters.

2. **Match the Algorithm to the Mathematical Structure**
   - **Hamiltonian / conservative systems**: prefer symplectic integrators (Velocity Verlet / Störmer-Verlet, Forest-Ruth, Gauss-Legendre implicit RK) over generic dissipative RK4 for long-time integration.
   - **Stiff ODEs / diffusion PDEs**: use implicit or BDF/Radau methods (`scipy.integrate.solve_ivp(..., method="Radau")` / `"BDF"`) or Crank-Nicolson / IMEX schemes; check CFL / stability limits explicitly.
   - **Spectral / smooth periodic PDEs**: FFT pseudospectral methods + dealiasing (2/3 rule) beat low-order finite differences by orders of magnitude.
   - **Monte Carlo / stochastic**: explicitly seed PRNGs (`np.random.default_rng(seed)`), report standard errors / autocorrelation-adjusted error bars, never point estimates alone.
   - **Heavy sweeps / autodiff**: use vectorized NumPy or optional JAX (`jit`/`vmap`) with `jax_enable_x64=True` — **never silently run theoretical physics accuracy checks in float32 unless precision sensitivity is explicitly tested.**

3. **Mandatory Verification Instrumentation**
   Every serious simulation lead should include checks (via `rpipe.helpers.checks`) for:
   - Grid / timestep convergence (`check_convergence_order` across at least 3 refinements, e.g., $h, h/2, h/4$).
   - Conservation / invariant drift (`check_conservation`).
   - Exact analytic limit (`check_analytic_limit`).
   - Sensitivity to boundary conditions / box size / truncation order.

4. **Output & Visualization Discipline**
   - Write all figures and summaries into `get_run_dir()` (from `rpipe.helpers.io`).
   - Use non-interactive Matplotlib backend (`matplotlib.use("Agg")`) so scripts work reliably headless via `rpipe run`.
   - Every plot must have labeled axes with units/dimensionless symbols, legend, readable font size, and log-scales where power laws or error convergence are displayed.
   - Never rely solely on visual inspection of a plot to claim a scaling law or conservation — compute quantitative slopes, $R^2$ / residual norms, and max absolute/relative errors into `summary.json`.
