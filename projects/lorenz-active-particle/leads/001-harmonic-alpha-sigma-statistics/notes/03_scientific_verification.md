# Stage 3 scientific verification

## Scope and provenance

Stage 3 used the approved model and parameter ranges without changing any success or
falsification threshold. All scientific computations were executed through `rpipe run`.
The principal evidence runs are:

- `runs/20261125T093355Z`: timestep, ODE tolerance, burn-in, trajectory-length, and
  initial ensemble-size refinements at $\sigma=\sqrt{50}$.
- `runs/20261125T093718Z`: a $10^4$-time-unit stationary record, density-estimator
  comparisons, and nested ensembles up to $N=10240$.
- `runs/20261125T094642Z`: fine-grid first-passage survival and tail-model diagnostics.
- `runs/20261125T094448Z`: initial consolidated Stage 3 gate evidence; superseded by
  the final consolidated run after the corrected tail classification was regenerated.
- `runs/20261125T094742Z`: final consolidated Stage 3 evidence.

The Stage 2 first-passage root finder was corrected after double-precision
`hyp2f1` produced a spurious root for large $\gamma/\mu$. Candidate roots are now
checked independently at high precision, with a high-precision fallback. The
first-passage survival grid was also refined to spacing $\leq0.1$ so tail slopes are
resolved. These are numerical-instrument corrections; the approved equations and
parameter domains are unchanged.

## Checks that passed

- Deterministic replay is bitwise identical for states and crossing times.
- Lorenz $(X,Y)\mapsto(-X,-Y)$ symmetry is exact to machine precision.
- The constant-sign harmonic filter agrees with its analytic solution to
  $7.8\times10^{-16}$ and preserves $|y|\leq1$ with zero measured excess.
- Tightening the ODE tolerances changes common crossing times by at most
  $1.6\times10^{-9}$ relatively.
- On a fixed chaotic realization, refining $\Delta t=0.01$ to $0.005$ changes the
  stationary second moment by at most $0.063\%$ across
  $\alpha\in\{0.05,0.25,1,5\}$.
- Increasing burn-in from 100 to 200 changes the reversal rate by $0.054\%$ and the
  slow $\alpha=0.05$ second moment by $0.045\%$ on the common long record.
- The reversal rate at $\sigma=\sqrt{50}$ changes by $0.050\%$ between 5000 and
  10000 time units.
- Symbolic and independent numerical checks of the RTP second and fourth moments
  agree to relative errors below $2.7\times10^{-16}$. The first-passage root has the
  correct small- and large-$\gamma/\mu$ limits at the declared tolerances.
- Nested $N=5120\to10240$ ensembles change the fitted relaxation rates by $1.22\%$
  (origin) and $2.73\%$ (half edge), and the descriptive first-passage fit by
  $0.055\%$; these satisfy the 5% numerical-refinement gate.

## Genuine falsifications established

At $\sigma=\sqrt{50}$, the effective-RTP stationary second-moment collapse is
falsified at the following converged points. Each discrepancy exceeds 10% and five
block standard errors after the timestep, burn-in, rate, and trajectory-length
checks pass:

| $\alpha$ | Lorenz $\langle y^2\rangle$ | RTP prediction | Relative discrepancy | $z$ score |
| :--- | ---: | ---: | ---: | ---: |
| 0.25 | 0.19753 | 0.30898 | -36.1% | 33.9 |
| 0.50 | 0.34510 | 0.47210 | -26.9% | 36.7 |
| 1.00 | 0.53888 | 0.64139 | -16.0% | 31.2 |

The first-passage survival at $(\sigma,\alpha)=(\sqrt{50},0.5)$ is numerically
converged, but a single exponential tail is rejected. Tail-rate estimates rise from
$0.700$ to $0.834$ as the threshold moves from the median to the 80th percentile,
a persistent $17.4\%$ spread. Windowed log-survival slopes show the same drift.
Accordingly, the apparent global fit rate near $0.75$ is descriptive and is not used
as an RTP exponent falsification.

## Unresolved points

- At $\sigma=\sqrt{50}$, $\alpha=0.05$ and $0.10$ remain unresolved: their second
  moments change by $4.82\%$ and $2.57\%$, respectively, between 5000 and 10000 time
  units, despite large and highly significant RTP discrepancies.
- Density modality is estimator-stable at $\alpha=0.10,0.25,0.50,0.75$ for the
  tested long record, but remains estimator-sensitive at $\alpha=1.0$. A complete
  uncertainty-qualified shape boundary is therefore not accepted.
- The other reversing Stage 2 values $\sigma=10$, $11.5307153908$, and
  $14.7245448086$ have not received comparable long-record, estimator, and ensemble
  refinements. Their Stage 2 moment discrepancies, boundaries, relaxation fits, and
  first-passage fits remain preliminary.
- Fixed, nonreversing, and multistable candidate regimes retain their Stage 2
  classification; no Poisson-rate comparison is made there.

The registered gate therefore remains failed only on full-sweep density-modality and
convergence completeness. The lead remains in `running` status. No Stage 4 evaluation
or verdict has been written.
