"""Multi-layer scientific verification gate for research leads."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from rpipe.runner import normalize_command
from rpipe.schemas import CheckOutcome, VerificationReport
from rpipe.workspace import load_lead

FORBIDDEN_LEAN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("sorry", re.compile(r"\bsorry\b")),
    ("admit", re.compile(r"\badmit\b")),
    ("axiom", re.compile(r"^\s*axiom\b", re.MULTILINE)),
    ("native_decide", re.compile(r"\bnative_decide\b")),
    ("implemented_by", re.compile(r"\bimplemented_by\b")),
]


def strip_lean_comments(source: str) -> str:
    """Strip Lean 4 nested block comments `/- ... -/` and line comments `-- ...`."""
    out: list[str] = []
    i = 0
    n = len(source)
    depth = 0
    while i < n:
        if depth == 0 and source[i : i + 2] == "--":
            newline = source.find("\n", i)
            if newline == -1:
                break
            out.append("\n")
            i = newline + 1
        elif source[i : i + 2] == "/-":
            depth += 1
            i += 2
        elif depth > 0 and source[i : i + 2] == "-/":
            depth -= 1
            i += 2
        elif depth == 0:
            out.append(source[i])
            i += 1
        else:
            if source[i] == "\n":
                out.append("\n")
            i += 1
    return "".join(out)


def audit_lean_source(lean_path: Path) -> CheckOutcome:
    """Static check ensuring a Lean 4 file has no `sorry`, `admit`, custom axioms, or escapes."""
    if not lean_path.exists():
        return CheckOutcome(
            name=f"lean-audit:{lean_path.name}",
            kind="lean_audit",
            status="failed",
            message=f"Declared Lean file not found: {lean_path}",
        )

    cleaned = strip_lean_comments(lean_path.read_text(encoding="utf-8"))
    hits: list[str] = [
        label for label, pattern in FORBIDDEN_LEAN_PATTERNS if pattern.search(cleaned)
    ]
    if hits:
        return CheckOutcome(
            name=f"lean-audit:{lean_path.name}",
            kind="lean_audit",
            status="failed",
            message=f"Forbidden Lean proof escape(s) detected: {', '.join(hits)}",
            details={"forbidden_tokens": hits},
        )
    return CheckOutcome(
        name=f"lean-audit:{lean_path.name}",
        kind="lean_audit",
        status="passed",
        message="No sorry/admit/axiom/native_decide escapes found.",
    )


def compile_lean_file(
    lean_path: Path,
    cwd: Path,
    *,
    require_lean: bool = False,
    timeout_sec: int = 180,
) -> CheckOutcome:
    """Compile a Lean 4 file if `lean` is available on PATH."""
    lean_bin = shutil.which("lean")
    if not lean_bin:
        return CheckOutcome(
            name=f"lean-compile:{lean_path.name}",
            kind="lean_compile",
            status="failed" if require_lean else "skipped",
            message=(
                "Lean 4 (`lean`) not found on PATH. "
                "Install Lean via elan to run kernel compilation."
            ),
        )

    t0 = time.perf_counter()
    proc = subprocess.run(
        [lean_bin, str(lean_path)],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        check=False,
    )
    dt = round(time.perf_counter() - t0, 4)
    if proc.returncode == 0:
        return CheckOutcome(
            name=f"lean-compile:{lean_path.name}",
            kind="lean_compile",
            status="passed",
            duration_sec=dt,
            message="Lean 4 kernel check succeeded.",
        )
    return CheckOutcome(
        name=f"lean-compile:{lean_path.name}",
        kind="lean_compile",
        status="failed",
        duration_sec=dt,
        message=(proc.stderr or proc.stdout).strip()[:1000],
    )


def verify_lead(
    lead_dir: Path,
    *,
    require_lean: bool = False,
) -> VerificationReport:
    """Run schema validation, pytest, declared checks, and Lean 4 checks for a lead."""
    outcomes: list[CheckOutcome] = []
    try:
        spec = load_lead(lead_dir)
        outcomes.append(
            CheckOutcome(
                name="lead-schema",
                kind="schema",
                status="passed",
                message="lead.yaml conforms to LeadSpec schema.",
            )
        )
    except Exception as exc:
        report = VerificationReport(
            lead_id=lead_dir.name,
            project_id=lead_dir.parent.parent.name,
            passed=False,
            outcomes=[
                CheckOutcome(
                    name="lead-schema",
                    kind="schema",
                    status="failed",
                    message=str(exc),
                )
            ],
        )
        return report

    env = os.environ.copy()
    env["RPIPE_LEAD_DIR"] = str(lead_dir.resolve())
    existing_py = env.get("PYTHONPATH", "")
    lead_str = str(lead_dir.resolve())
    env["PYTHONPATH"] = f"{lead_str}{os.pathsep}{existing_py}" if existing_py else lead_str
    env["PYTHONUTF8"] = "1"
    env.setdefault("MPLBACKEND", "Agg")

    # 1. pytest on work/
    if spec.verification.pytest:
        work_dir = lead_dir / "work"
        test_files = list(work_dir.glob("test_*.py")) + list(work_dir.glob("*_test.py"))
        if not test_files:
            outcomes.append(
                CheckOutcome(
                    name="pytest",
                    kind="pytest",
                    status="skipped",
                    message="No test_*.py files found in work/.",
                )
            )
        else:
            t0 = time.perf_counter()
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "work"],
                cwd=lead_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
            dt = round(time.perf_counter() - t0, 4)
            outcomes.append(
                CheckOutcome(
                    name="pytest",
                    kind="pytest",
                    status="passed" if proc.returncode == 0 else "failed",
                    duration_sec=dt,
                    message=(proc.stdout + proc.stderr).strip()[:1000],
                )
            )

    # 2. Custom verification checks declared in lead.yaml
    for check in spec.verification.checks:
        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                normalize_command(check.command),
                cwd=lead_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=check.timeout_sec,
                check=False,
            )
            dt = round(time.perf_counter() - t0, 4)
            combined = (proc.stdout + proc.stderr).strip()
            msg = combined[-1500:] if proc.returncode != 0 else combined[:1000]
            outcomes.append(
                CheckOutcome(
                    name=check.name,
                    kind="custom",
                    status="passed" if proc.returncode == 0 else "failed",
                    duration_sec=dt,
                    message=msg,
                )
            )
        except subprocess.TimeoutExpired:
            outcomes.append(
                CheckOutcome(
                    name=check.name,
                    kind="custom",
                    status="failed",
                    duration_sec=float(check.timeout_sec),
                    message=f"Check timed out after {check.timeout_sec}s.",
                )
            )

    # 3. Lean 4 static audit + kernel compilation
    for rel_lean in spec.verification.lean_files:
        lean_path = lead_dir / rel_lean
        audit = audit_lean_source(lean_path)
        outcomes.append(audit)
        if audit.status == "passed":
            outcomes.append(compile_lean_file(lean_path, lead_dir, require_lean=require_lean))

    passed = all(o.status != "failed" for o in outcomes)
    report = VerificationReport(
        lead_id=spec.id,
        project_id=spec.project,
        passed=passed,
        outcomes=outcomes,
    )

    runs_dir = lead_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / "latest_verification.json").write_text(
        report.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    return report
