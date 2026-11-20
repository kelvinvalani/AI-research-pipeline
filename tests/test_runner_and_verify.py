"""Tests for subprocess execution, provenance capture, and verification gate."""

from __future__ import annotations

import json
from pathlib import Path

from rpipe.runner import run_in_lead
from rpipe.schemas import CheckSpec, LeadSpec, VerificationConfig
from rpipe.verify import audit_lean_source, strip_lean_comments, verify_lead
from rpipe.workspace import save_lead


def _make_lead(tmp_path: Path, *, lean_files: list[str] | None = None) -> Path:
    lead_dir = tmp_path / "projects" / "demo" / "leads" / "001-run"
    (lead_dir / "work").mkdir(parents=True)
    (lead_dir / "runs").mkdir(parents=True)
    spec = LeadSpec(
        id="001-run",
        project="demo",
        title="Runner Test",
        verification=VerificationConfig(
            pytest=True,
            lean_files=lean_files or [],
            checks=[
                CheckSpec(name="inline-check", command=["python", "-c", "print('ok')"]),
            ],
        ),
    )
    save_lead(lead_dir, spec)
    return lead_dir


def test_run_captures_manifest_summary_and_ledger(tmp_path: Path) -> None:
    lead_dir = _make_lead(tmp_path)
    script = lead_dir / "work" / "job.py"
    script.write_text(
        "from rpipe.helpers.io import get_seed, save_summary\n"
        "save_summary({'seed': get_seed(), 'value': 3.14})\n"
        "print('hello run')\n",
        encoding="utf-8",
    )

    manifest = run_in_lead(lead_dir, ["python", "work/job.py"], seed=123, tag="smoke")
    assert manifest.exit_code == 0
    assert manifest.seed == 123
    assert manifest.summary == {"seed": 123, "value": 3.14}

    run_dir = lead_dir / manifest.run_dir
    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "stdout.log").read_text(encoding="utf-8").strip() == "hello run"
    ledger_lines = (lead_dir / "runs" / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(ledger_lines) == 1
    assert json.loads(ledger_lines[0])["run_id"] == manifest.run_id


def test_lean_audit_catches_sorry_and_ignores_comments(tmp_path: Path) -> None:
    clean_file = tmp_path / "Clean.lean"
    clean_file.write_text(
        "-- sorry in a line comment is fine\n"
        "/- nested /- sorry -/ block comment is fine -/\n"
        "theorem ok : 1 + 1 = 2 := by rfl\n",
        encoding="utf-8",
    )
    assert "sorry" not in strip_lean_comments(clean_file.read_text(encoding="utf-8"))
    assert audit_lean_source(clean_file).status == "passed"

    bad_file = tmp_path / "Bad.lean"
    bad_file.write_text("theorem cheat : 1 = 2 := by sorry\n", encoding="utf-8")
    res = audit_lean_source(bad_file)
    assert res.status == "failed"
    assert "sorry" in res.details["forbidden_tokens"]


def test_verify_lead_passes_with_tests_checks_and_clean_lean(tmp_path: Path) -> None:
    lead_dir = _make_lead(tmp_path, lean_files=["work/Proof.lean"])
    (lead_dir / "work" / "test_sample.py").write_text(
        "def test_math():\n    assert 2 + 2 == 4\n", encoding="utf-8"
    )
    (lead_dir / "work" / "Proof.lean").write_text(
        "theorem id_nat (n : Nat) : n = n := rfl\n", encoding="utf-8"
    )

    report = verify_lead(lead_dir, require_lean=False)
    assert report.passed is True
    assert (lead_dir / "runs" / "latest_verification.json").exists()
