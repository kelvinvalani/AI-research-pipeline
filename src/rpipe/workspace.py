"""Workspace discovery, project/lead scaffolding, and status inspection."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from rpipe.refs import list_inbox_files
from rpipe.schemas import LeadKind, LeadSpec, LeadStatus, ProjectMeta, utc_now_iso

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def find_repo_root(start: Path | None = None) -> Path:
    """Walk upward from `start` (or CWD) to locate the repository root."""
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists() and (candidate / "templates").exists():
            return candidate
        if (candidate / ".git").exists():
            return candidate
    return current


def _validate_slug(slug: str, label: str) -> str:
    if not SLUG_RE.match(slug):
        raise ValueError(
            f"Invalid {label} slug '{slug}'. Use lowercase letters, digits, '-' or '_'."
        )
    return slug


def _render_template(text: str, replacements: dict[str, str]) -> str:
    rendered = text
    for key, value in replacements.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def init_project(
    project_id: str,
    title: str,
    summary: str = "",
    repo_root: Path | None = None,
) -> Path:
    """Scaffold a new research project under `projects/<project_id>/`."""
    _validate_slug(project_id, "project")
    root = find_repo_root(repo_root)
    project_dir = root / "projects" / project_id
    if project_dir.exists():
        raise FileExistsError(f"Project already exists: {project_dir}")

    template_dir = root / "templates" / "project"
    created_at = utc_now_iso()
    replacements = {
        "PROJECT_ID": project_id,
        "PROJECT_TITLE": title,
        "PROJECT_SUMMARY": summary or "Theoretical math/physics research project.",
        "CREATED_AT": created_at,
    }

    (project_dir / "leads").mkdir(parents=True, exist_ok=True)
    (project_dir / "refs").mkdir(parents=True, exist_ok=True)
    for rel in ("project.yaml", "README.md", "refs/README.md"):
        src = template_dir / rel
        dst = project_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.exists():
            content = _render_template(src.read_text(encoding="utf-8"), replacements)
        elif rel == "project.yaml":
            meta = ProjectMeta(
                id=project_id, title=title, summary=summary, created_at=created_at
            )
            content = yaml.safe_dump(meta.model_dump(), sort_keys=False)
        elif rel == "refs/README.md":
            content = f"# Project References (`refs/`)\n\nShared papers and files for {title}.\n"
        else:
            content = f"# {title}\n\n> {summary}\n"
        dst.write_text(content, encoding="utf-8")

    return project_dir


def new_lead(
    project_id: str,
    lead_id: str,
    title: str,
    kind: LeadKind = LeadKind.HYBRID,
    repo_root: Path | None = None,
) -> Path:
    """Scaffold a new 5-zone research lead under `projects/<project_id>/leads/<lead_id>/`."""
    _validate_slug(project_id, "project")
    _validate_slug(lead_id, "lead")
    root = find_repo_root(repo_root)
    project_dir = root / "projects" / project_id
    if not (project_dir / "project.yaml").exists():
        raise FileNotFoundError(
            f"Project '{project_id}' does not exist. Run `rpipe init-project {project_id}` first."
        )

    lead_dir = project_dir / "leads" / lead_id
    if lead_dir.exists():
        raise FileExistsError(f"Lead already exists: {lead_dir}")

    template_dir = root / "templates" / "lead"
    created_at = utc_now_iso()
    replacements = {
        "PROJECT_ID": project_id,
        "LEAD_ID": lead_id,
        "LEAD_TITLE": title,
        "LEAD_KIND": kind.value,
        "CREATED_AT": created_at,
    }

    for sub in ("notes", "work", "runs"):
        (lead_dir / sub).mkdir(parents=True, exist_ok=True)

    template_files = (
        "lead.yaml",
        "notes/01_background.md",
        "work/README.md",
        "evaluation.md",
    )
    for rel in template_files:
        src = template_dir / rel
        dst = lead_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.exists():
            content = _render_template(src.read_text(encoding="utf-8"), replacements)
            dst.write_text(content, encoding="utf-8")

    if not (lead_dir / "lead.yaml").exists():
        spec = LeadSpec(
            id=lead_id,
            project=project_id,
            title=title,
            kind=kind,
            created_at=created_at,
        )
        save_lead(lead_dir, spec)

    return lead_dir


def load_project(project_dir: Path) -> ProjectMeta:
    data = yaml.safe_load((project_dir / "project.yaml").read_text(encoding="utf-8"))
    return ProjectMeta.model_validate(data)


def load_lead(lead_dir: Path) -> LeadSpec:
    lead_yaml = lead_dir / "lead.yaml"
    if not lead_yaml.exists():
        raise FileNotFoundError(f"Missing lead.yaml in {lead_dir}")
    data = yaml.safe_load(lead_yaml.read_text(encoding="utf-8"))
    return LeadSpec.model_validate(data)


def save_lead(lead_dir: Path, spec: LeadSpec) -> None:
    content = yaml.safe_dump(
        spec.model_dump(mode="json"),
        sort_keys=False,
        allow_unicode=True,
    )
    (lead_dir / "lead.yaml").write_text(content, encoding="utf-8")


def set_lead_status(lead_dir: Path, status: LeadStatus) -> LeadSpec:
    spec = load_lead(lead_dir)
    spec.status = status
    save_lead(lead_dir, spec)
    return spec


def resolve_lead_dir(lead_ref: str | Path, repo_root: Path | None = None) -> Path:
    """Resolve a lead directory from a path or `<project>/<lead>` shorthand."""
    path = Path(lead_ref)
    if (path / "lead.yaml").exists():
        return path.resolve()

    root = find_repo_root(repo_root)
    candidate = root / path
    if (candidate / "lead.yaml").exists():
        return candidate.resolve()

    parts = Path(lead_ref).parts
    if len(parts) == 2:
        shorthand = root / "projects" / parts[0] / "leads" / parts[1]
        if (shorthand / "lead.yaml").exists():
            return shorthand.resolve()

    raise FileNotFoundError(f"Could not locate lead directory for '{lead_ref}'.")


def workspace_status(
    repo_root: Path | None = None,
    project_filter: str | None = None,
) -> dict[str, Any]:
    """Return a structured overview of all projects, leads, and latest runs/verifications."""
    root = find_repo_root(repo_root)
    projects_root = root / "projects"
    projects_out: list[dict[str, Any]] = []

    if projects_root.exists():
        for proj_dir in sorted(p for p in projects_root.iterdir() if p.is_dir()):
            if project_filter and proj_dir.name != project_filter:
                continue
            if not (proj_dir / "project.yaml").exists():
                continue
            meta = load_project(proj_dir)
            leads_out: list[dict[str, Any]] = []
            leads_root = proj_dir / "leads"
            if leads_root.exists():
                for lead_dir in sorted(p for p in leads_root.iterdir() if p.is_dir()):
                    if not (lead_dir / "lead.yaml").exists():
                        continue
                    spec = load_lead(lead_dir)
                    ledger = lead_dir / "runs" / "ledger.jsonl"
                    run_count = (
                        sum(1 for line in ledger.read_text(encoding="utf-8").splitlines() if line)
                        if ledger.exists()
                        else 0
                    )
                    verify_file = lead_dir / "runs" / "latest_verification.json"
                    verified_flag: bool | None = None
                    if verify_file.exists():
                        import json

                        verified_flag = bool(
                            json.loads(verify_file.read_text(encoding="utf-8")).get("passed")
                        )
                    leads_out.append(
                        {
                            "id": spec.id,
                            "title": spec.title,
                            "kind": spec.kind.value,
                            "status": spec.status.value,
                            "runs": run_count,
                            "last_verify_passed": verified_flag,
                            "path": str(lead_dir.relative_to(root).as_posix()),
                        }
                    )
            projects_out.append(
                {
                    "id": meta.id,
                    "title": meta.title,
                    "status": meta.status,
                    "summary": meta.summary,
                    "leads": leads_out,
                }
            )

    return {
        "repo_root": str(root.as_posix()),
        "inbox_files": list_inbox_files(root),
        "projects": projects_out,
    }
