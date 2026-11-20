"""Tests for workspace scaffolding and CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rpipe.cli import main as cli_main
from rpipe.schemas import LeadKind, LeadStatus
from rpipe.workspace import (
    init_project,
    load_lead,
    new_lead,
    resolve_lead_dir,
    set_lead_status,
    workspace_status,
)


def _setup_mini_repo(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / "templates" / "project").mkdir(parents=True)
    (tmp_path / "templates" / "lead" / "notes").mkdir(parents=True)
    (tmp_path / "templates" / "lead" / "work").mkdir(parents=True)
    (tmp_path / "templates" / "project" / "project.yaml").write_text(
        'id: "{{PROJECT_ID}}"\ntitle: "{{PROJECT_TITLE}}"\nsummary: "{{PROJECT_SUMMARY}}"\n',
        encoding="utf-8",
    )
    (tmp_path / "templates" / "project" / "README.md").write_text(
        "# {{PROJECT_TITLE}}\n", encoding="utf-8"
    )
    (tmp_path / "templates" / "lead" / "lead.yaml").write_text(
        'id: "{{LEAD_ID}}"\n'
        'project: "{{PROJECT_ID}}"\n'
        'title: "{{LEAD_TITLE}}"\n'
        'kind: "{{LEAD_KIND}}"\n',
        encoding="utf-8",
    )
    (tmp_path / "templates" / "lead" / "notes" / "01_background.md").write_text(
        "# Notes\n", encoding="utf-8"
    )
    (tmp_path / "templates" / "lead" / "work" / "README.md").write_text(
        "# Work\n", encoding="utf-8"
    )
    (tmp_path / "templates" / "lead" / "evaluation.md").write_text("# Eval\n", encoding="utf-8")
    return tmp_path


def test_scaffold_project_and_lead(tmp_path: Path) -> None:
    root = _setup_mini_repo(tmp_path)
    proj_dir = init_project("quantum-chaos", title="Quantum Chaos", repo_root=root)
    assert (proj_dir / "project.yaml").exists()

    lead_dir = new_lead(
        "quantum-chaos",
        "001-level-spacing",
        title="Level Spacing Statistics",
        kind=LeadKind.NUMERICAL,
        repo_root=root,
    )
    for expected in ("lead.yaml", "notes/01_background.md", "work/README.md", "evaluation.md"):
        assert (lead_dir / expected).exists()

    spec = load_lead(lead_dir)
    assert spec.kind == LeadKind.NUMERICAL
    assert resolve_lead_dir("quantum-chaos/001-level-spacing", repo_root=root) == lead_dir.resolve()

    updated = set_lead_status(lead_dir, LeadStatus.CONFIRMED)
    assert updated.status == LeadStatus.CONFIRMED

    status = workspace_status(repo_root=root)
    assert len(status["projects"]) == 1
    assert status["projects"][0]["leads"][0]["status"] == "confirmed"


def test_invalid_slug_rejected(tmp_path: Path) -> None:
    root = _setup_mini_repo(tmp_path)
    with pytest.raises(ValueError, match="Invalid project slug"):
        init_project("Bad Slug!", title="Invalid", repo_root=root)


def test_cli_status_json(capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli_main(["status", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert "projects" in payload


def test_split_run_argv_variants() -> None:
    from rpipe.cli import _split_run_argv

    head1, cmd1 = _split_run_argv(
        ["run", "proj/lead", "--tag", "base", "--", "python", "work/sim.py", "--n", "10"]
    )
    assert head1 == ["run", "proj/lead", "--tag", "base"]
    assert cmd1 == ["python", "work/sim.py", "--n", "10"]

    # PowerShell strips bare `--`; splitting should still work cleanly
    head2, cmd2 = _split_run_argv(
        ["run", "proj/lead", "--tag", "base", "python", "work/sim.py", "--n", "10"]
    )
    assert head2 == ["run", "proj/lead", "--tag", "base"]
    assert cmd2 == ["python", "work/sim.py", "--n", "10"]
