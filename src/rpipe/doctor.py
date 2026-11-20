"""Environment health check (`rpipe doctor`) for non-developer researchers and agents."""

from __future__ import annotations

import importlib.util
import platform
import shutil
import sys
from pathlib import Path
from typing import Any

from rpipe.workspace import find_repo_root

REQUIRED_MODULES: list[tuple[str, str, str]] = [
    ("pydantic", "pydantic", "Schema validation"),
    ("yaml", "pyyaml", "YAML lead/project specs"),
    ("pypdf", "pypdf", "PDF reference inspection"),
    ("numpy", "numpy", "Numerical arrays & linear algebra"),
    ("scipy", "scipy", "ODE/PDE solvers & scientific computing"),
    ("matplotlib", "matplotlib", "Publication figures"),
    ("sympy", "sympy", "Symbolic mathematics & algebra"),
    ("z3", "z3-solver", "SMT theorem proving & counterexample search"),
    ("pytest", "pytest", "Automated verification tests"),
]

OPTIONAL_TOOLS: list[tuple[str, str, str]] = [
    ("jax", "module", "Optional GPU/autodiff acceleration (`uv sync --extra all --extra jax`)"),
    ("lean", "binary", "Optional Lean 4 formal proof compiler (install via elan)"),
    ("lake", "binary", "Optional Lean 4 build manager (install via elan)"),
]


def _has_module(mod_name: str) -> bool:
    return importlib.util.find_spec(mod_name) is not None


def run_doctor(repo_root: Path | None = None) -> dict[str, Any]:
    """Check Python, uv, git, required math/physics libraries, and optional tools."""
    root = find_repo_root(repo_root)
    checks: list[dict[str, Any]] = []

    py_ver = platform.python_version()
    py_ok = sys.version_info >= (3, 11)
    checks.append(
        {
            "name": "python>=3.11",
            "category": "runtime",
            "status": "ok" if py_ok else "missing",
            "detail": f"Python {py_ver} ({sys.executable})",
        }
    )

    for binary, desc in (("uv", "Fast Python environment manager"), ("git", "Provenance tracking")):
        loc = shutil.which(binary)
        checks.append(
            {
                "name": binary,
                "category": "runtime",
                "status": "ok" if loc else "missing",
                "detail": loc or f"{desc} not found on PATH",
            }
        )

    venv_exists = (root / ".venv").exists()
    checks.append(
        {
            "name": ".venv",
            "category": "runtime",
            "status": "ok" if venv_exists else "missing",
            "detail": (
                str((root / ".venv").as_posix())
                if venv_exists
                else "Run `.\\setup.ps1` (Windows) or `uv sync --extra all --extra dev`"
            ),
        }
    )

    for mod_name, pkg_name, purpose in REQUIRED_MODULES:
        present = _has_module(mod_name)
        detail = purpose if present else f"Missing ({purpose}) — run `uv sync --extra all`"
        checks.append(
            {
                "name": pkg_name,
                "category": "required_package",
                "status": "ok" if present else "missing",
                "detail": detail,
            }
        )

    for name, kind, hint in OPTIONAL_TOOLS:
        present = _has_module(name) if kind == "module" else bool(shutil.which(name))
        checks.append(
            {
                "name": name,
                "category": "optional",
                "status": "ok" if present else "optional_missing",
                "detail": "Installed" if present else hint,
            }
        )

    ready = all(c["status"] == "ok" for c in checks if c["category"] != "optional")
    return {
        "ready": ready,
        "repo_root": root.as_posix(),
        "checks": checks,
    }
