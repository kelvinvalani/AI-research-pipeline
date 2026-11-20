"""Tests for environment health check (`rpipe doctor`)."""

from __future__ import annotations

import json

import pytest

from rpipe.cli import main as cli_main
from rpipe.doctor import run_doctor


def test_run_doctor_reports_ready() -> None:
    report = run_doctor()
    assert report["ready"] is True
    names = {c["name"] for c in report["checks"]}
    assert {"python>=3.11", "uv", "numpy", "scipy", "sympy", "z3-solver", "pypdf"} <= names


def test_cli_doctor_json(capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli_main(["doctor", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ready"] is True
