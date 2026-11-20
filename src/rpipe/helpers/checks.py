"""Domain-general scientific sanity & mathematical verification helpers."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class CheckResult:
    name: str
    passed: bool
    message: str
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def check_conservation(
    values: Sequence[float],
    *,
    name: str = "conservation",
    rtol: float = 1e-6,
    atol: float = 1e-10,
) -> CheckResult:
    """Check that a conserved quantity (e.g. energy, probability norm) stays constant."""
    if len(values) < 2:
        return CheckResult(name=name, passed=False, message="Need at least 2 samples.")

    ref = float(values[0])
    max_abs = max(abs(float(v) - ref) for v in values)
    denom = max(abs(ref), 1e-30)
    max_rel = max_abs / denom
    passed = max_abs <= atol + rtol * abs(ref)
    return CheckResult(
        name=name,
        passed=passed,
        message=(
            f"max_abs_drift={max_abs:.3e}, max_rel_drift={max_rel:.3e} "
            f"(rtol={rtol:.1e}, atol={atol:.1e})"
        ),
        metrics={"reference": ref, "max_abs_drift": max_abs, "max_rel_drift": max_rel},
    )


def check_convergence_order(
    step_sizes: Sequence[float],
    errors: Sequence[float],
    *,
    expected_order: float,
    order_tol: float = 0.25,
    name: str = "convergence_order",
) -> CheckResult:
    """Verify empirical convergence rate p in error(h) ~ C * h^p across >= 3 step sizes."""
    if len(step_sizes) != len(errors) or len(step_sizes) < 3:
        return CheckResult(
            name=name,
            passed=False,
            message="Provide at least 3 matching (step_size, error) pairs.",
        )

    pairs = sorted(zip(step_sizes, errors, strict=True), key=lambda p: p[0], reverse=True)
    if any(h <= 0 or e <= 0 for h, e in pairs):
        return CheckResult(
            name=name,
            passed=False,
            message="Step sizes and errors must all be strictly positive.",
        )

    log_h = [math.log(h) for h, _ in pairs]
    log_e = [math.log(e) for _, e in pairs]
    mean_x = sum(log_h) / len(log_h)
    mean_y = sum(log_e) / len(log_e)
    sxx = sum((x - mean_x) ** 2 for x in log_h)
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(log_h, log_e, strict=True))
    slope = sxy / sxx

    pairwise_orders = [
        math.log(pairs[i][1] / pairs[i + 1][1]) / math.log(pairs[i][0] / pairs[i + 1][0])
        for i in range(len(pairs) - 1)
    ]
    passed = abs(slope - expected_order) <= order_tol
    return CheckResult(
        name=name,
        passed=passed,
        message=(
            f"measured_order={slope:.3f} vs expected={expected_order:.3f} (tol=±{order_tol:.3f})"
        ),
        metrics={
            "measured_order": round(slope, 4),
            "expected_order": expected_order,
            "pairwise_orders": [round(p, 4) for p in pairwise_orders],
        },
    )


def check_analytic_limit(
    numerical_values: Sequence[float],
    analytic_values: Sequence[float],
    *,
    rtol: float = 1e-5,
    atol: float = 1e-8,
    name: str = "analytic_limit",
) -> CheckResult:
    """Compare numerical outputs against a known closed-form analytic limit."""
    if len(numerical_values) != len(analytic_values) or len(numerical_values) == 0:
        return CheckResult(name=name, passed=False, message="Mismatched or empty sequences.")

    abs_errs = [
        abs(float(n) - float(a))
        for n, a in zip(numerical_values, analytic_values, strict=True)
    ]
    max_abs = max(abs_errs)
    max_scale = max(max(abs(float(a)) for a in analytic_values), 1e-30)
    max_rel = max_abs / max_scale
    passed = all(
        abs(float(n) - float(a)) <= atol + rtol * abs(float(a))
        for n, a in zip(numerical_values, analytic_values, strict=True)
    )
    return CheckResult(
        name=name,
        passed=passed,
        message=f"max_abs_err={max_abs:.3e}, max_rel_err={max_rel:.3e}",
        metrics={"max_abs_err": max_abs, "max_rel_err": max_rel},
    )


def check_symmetry(
    f_original: Sequence[float],
    f_transformed: Sequence[float],
    *,
    sign: float = 1.0,
    rtol: float = 1e-7,
    atol: float = 1e-10,
    name: str = "symmetry",
) -> CheckResult:
    """Check even (sign=+1) or odd (sign=-1) symmetry: f(T(x)) == sign * f(x)."""
    expected = [sign * float(v) for v in f_original]
    return check_analytic_limit(f_transformed, expected, rtol=rtol, atol=atol, name=name)


def check_symbolic_numeric_agreement(
    lhs_expr: Any,
    rhs_expr: Any,
    samples: Sequence[dict[Any, float]],
    *,
    rtol: float = 1e-9,
    atol: float = 1e-11,
    name: str = "symbolic_numeric_agreement",
) -> CheckResult:
    """Cross-check two SymPy expressions (or callables) numerically across generic sample points."""
    if not samples:
        return CheckResult(name=name, passed=False, message="Need at least 1 sample point.")

    max_abs = 0.0
    max_rel = 0.0
    for pt in samples:
        lhs_val = complex(lhs_expr.subs(pt).evalf(25)) if hasattr(lhs_expr, "subs") else complex(
            lhs_expr(**pt)
        )
        rhs_val = complex(rhs_expr.subs(pt).evalf(25)) if hasattr(rhs_expr, "subs") else complex(
            rhs_expr(**pt)
        )
        err = abs(lhs_val - rhs_val)
        scale = max(abs(rhs_val), 1e-30)
        max_abs = max(max_abs, err)
        max_rel = max(max_rel, err / scale)
        if err > atol + rtol * abs(rhs_val):
            return CheckResult(
                name=name,
                passed=False,
                message=f"Disagreement at {pt}: lhs={lhs_val}, rhs={rhs_val}, err={err:.3e}",
                metrics={"failed_point": str(pt), "max_abs_err": err, "max_rel_err": err / scale},
            )

    return CheckResult(
        name=name,
        passed=True,
        message=f"Matched across {len(samples)} sample points (max_abs={max_abs:.3e}).",
        metrics={"n_samples": len(samples), "max_abs_err": max_abs, "max_rel_err": max_rel},
    )


def run_check_suite(checks: Sequence[Callable[[], CheckResult]]) -> tuple[bool, list[CheckResult]]:
    """Run a list of zero-argument check callables and return `(all_passed, results)`."""
    results = [fn() for fn in checks]
    return all(r.passed for r in results), results
