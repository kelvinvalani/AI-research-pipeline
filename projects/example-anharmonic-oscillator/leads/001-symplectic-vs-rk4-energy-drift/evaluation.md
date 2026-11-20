# Lead Evaluation — Symplectic Verlet vs. RK4 Long-Time Energy Drift

- **Lead ID**: `001-symplectic-vs-rk4-energy-drift`
- **Project**: `example-anharmonic-oscillator`
- **Final Verdict**: `CONFIRMED`
- **Verification Gate**: `PASS` (`runs/latest_verification.json`)
- **Key Run(s)**: `runs/20261120T143737Z_baseline`

---

## 1. Executive Summary

We tested whether 2nd-order symplectic Velocity Verlet avoids secular energy drift over $T = 500$ ($h = 0.25$) on the quartic anharmonic oscillator ($\omega = 1, \lambda = 1, q_0 = 1.5, p_0 = 0$) compared with classical 4th-order RK4. **Confirmed**: Verlet's energy oscillation envelope stayed completely stationary (`late/early = 1.0000`, max error `0.1227`), whereas RK4 drifted monotonically to a final energy error of `0.7173` (`5.85x` Verlet's maximum error).

## 2. Evaluation Against Criteria

| Criterion (`lead.yaml`) | Evidence / Metric / Proof | Status |
| :--- | :--- | :--- |
| Verlet late-time max error $\le 1.5\times$ early-time max error | `verlet_early_max_err = 0.1227085`, `verlet_late_max_err = 0.12270701`, ratio `1.0000` (`runs/20261120T143737Z_baseline/summary.json`) | **MET** |
| RK4 final drift $> 2\times$ Verlet max error at $h=0.25, T=500$ | `rk4_final_err = 0.71731422` vs `verlet_overall_max_err = 0.12270889`, ratio `5.8457` | **MET** |
| All independent verification checks pass | `rpipe verify` passed `lead-schema`, `pytest` (3/3), and all 5 physics/math checks (`harmonic_analytic_limit`, `verlet_order`, `rk4_order`, `verlet_time_reversal` + `verlet_bounded_energy`, `symbolic_dH_dt_zero`) | **MET** |

## 3. Key Results

- Initial energy: $H(1.5, 0) = 2.390625$
- Velocity Verlet max energy error over $t \in [0, 500]$: `0.12270889` (purely oscillatory, zero drift)
- RK4 final energy error at $t = 500$: `0.71731422` (monotonic secular drift)
- Comparison plot saved at `runs/20261120T143737Z_baseline/energy_drift.png`

## 4. Verification Audit

- **Analytic harmonic limit ($\lambda = 0$)**: `max_abs_err = 2.860e-5`, `max_rel_err = 2.383e-5` (PASS).
- **Empirical convergence orders**:
  - Velocity Verlet: measured $p = 2.0002$ (pairwise `[1.998, 2.0001, 2.0026]`, expected `2.0 ± 0.15`) (PASS).
  - Classical RK4: measured $p = 4.0760$ (pairwise `[4.099, 4.0797, 4.0481]`, expected `4.0 ± 0.20`) (PASS).
- **Time-reversal symmetry & bounded energy**: forward-backward Verlet integration recovers $(q_0, p_0)$ to $< 10^{-11}$ (PASS).
- **Symbolic cross-check**: SymPy confirms $\frac{dH}{dt} = \{H, H\} = 0$ identically and numerically across generic test points (`max_abs_err = 0.0`) (PASS).
- **Caveats**: Single parameter point tested ($h = 0.25, \omega = \lambda = 1$); near the Verlet stability threshold $h \cdot \omega_{\text{eff}} \approx 2$, Verlet becomes unstable.

## 5. Next Leads & Promotion Decisions

- **Proposed Follow-Up Leads**:
  1. `002-lyapunov-stability-bound` (`formal`): machine-verify global Lyapunov positivity and exact $(q, p)$ bounds for all $\omega > 0, \lambda > 0$.
  2. `003-shadow-hamiltonian-expansion` (`symbolic` + `numerical`): derive the 2nd-order modified Hamiltonian $\tilde{H} = H + h^2 H_2$ via Baker–Campbell–Hausdorff and confirm $\tilde{H}$ is conserved to $O(h^4)$ along Verlet trajectories.
- **Promote to `src/rpipe/shared/`?**: Not yet — keep the 1D Verlet/RK4 helpers local until needed by a second independent project.
