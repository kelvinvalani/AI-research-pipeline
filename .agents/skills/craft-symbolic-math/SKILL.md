---
name: craft-symbolic-math
description: >-
  Craft skill for computer algebra and symbolic derivations in Python (SymPy):
  explicit domain assumptions, avoiding simplification traps, differential/series
  calculations, and mandatory numerical cross-checks.
---

# Craft: Symbolic Mathematics (SymPy)

Load this skill when performing symbolic algebra, calculus, perturbative expansions, tensor/matrix calculations, or exact identity verification in `work/`.

## Best Practices & Pitfalls

1. **Declare Symbol Assumptions Explicitly**
   Never use bare `sp.symbols("x")` when variables are real, positive, or integer:
   ```python
   x, m, omega = sp.symbols("x m omega", real=True, positive=True)
   n = sp.symbols("n", integer=True, nonnegative=True)
   ```
   Missing assumptions cause `sqrt(x**2)` not to simplify, branch-cut errors, or spurious complex solutions.

2. **Watch Out for Symbolic Simplification Traps**
   - `sp.simplify(expr)` can be slow or fail to recognize zero for trigonometric/hyperbolic/radical expressions. Combine targeted transforms (`expand`, `factor`, `trigsimp`, `radsimp`, `cancel`, `nsimplify`, `powsimp`).
   - Never assume `expr1 == expr2` tests mathematical equivalence — `==` in SymPy checks *structural* equality! Always test `sp.simplify(expr1 - expr2) == 0` AND confirm numerically.

3. **Mandatory Numerical Spot-Checking**
   Whenever you derive a symbolic identity, derivative, integral, or perturbative coefficient, cross-check it using `rpipe.helpers.checks.check_symbolic_numeric_agreement`:
   - Sample 5–20 random generic points in the valid domain (avoiding $0, 1, -1, \pi/2$ where bugs cancel).
   - Compare with high-precision evaluation (`mpmath` / `evalf(30)`) or finite differences / quadrature.

4. **Check Perturbative & Asymptotic Expansions Carefully**
   - Track truncation order explicitly (`sp.series(expr, eps, 0, n=6)`).
   - Verify that lower-order terms match known textbook limits and that substituting the truncated series back into the governing equation cancels residuals through the claimed order $O(\epsilon^k)$.

5. **Artifact Outputs**
   - Export key verified formulas in both human-readable LaTeX (`sp.latex(expr)`) and plain text inside `summary.json` or a generated `.tex`/`.md` snippet in `RPIPE_RUN_DIR` so `evaluation.md` quotes exact machine-verified equations rather than hand-transcribed ones.
