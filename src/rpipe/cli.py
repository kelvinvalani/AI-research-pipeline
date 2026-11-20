"""Thin, LLM-friendly CLI for managing projects, leads, runs, and scientific verification."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from rpipe.runner import run_in_lead
from rpipe.schemas import LeadKind, LeadStatus
from rpipe.verify import verify_lead
from rpipe.workspace import (
    init_project,
    new_lead,
    resolve_lead_dir,
    set_lead_status,
    workspace_status,
)


def _print_status_human(data: dict) -> None:
    projects = data.get("projects", [])
    if not projects:
        print("No projects found. Start one with: rpipe init-project <slug> --title '...'")
        return

    for proj in projects:
        print(f"\n[{proj['id']}] {proj['title']} ({proj['status']})")
        if proj.get("summary"):
            print(f"  {proj['summary']}")
        leads = proj.get("leads", [])
        if not leads:
            print("  (no leads yet)")
            continue
        for lead in leads:
            v_badge = (
                "PASS"
                if lead["last_verify_passed"] is True
                else ("FAIL" if lead["last_verify_passed"] is False else "----")
            )
            print(
                f"  - {lead['id']} | {lead['kind']:11s} | {lead['status']:12s} | "
                f"runs={lead['runs']} | verify={v_badge} | {lead['title']}"
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rpipe",
        description="Lean agent-native research pipeline for theoretical math & physics.",
    )
    sub = parser.add_subparsers(dest="subcommand", required=True)

    # status
    p_status = sub.add_parser("status", help="Show all projects, leads, and verification status.")
    p_status.add_argument("--project", default=None, help="Filter to a single project slug.")
    p_status.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")

    # init-project
    p_proj = sub.add_parser("init-project", help="Scaffold a new research project.")
    p_proj.add_argument("project_id", help="Lowercase project slug (e.g. nonlinear-waves).")
    p_proj.add_argument("--title", required=True, help="Human-readable project title.")
    p_proj.add_argument("--summary", default="", help="One-sentence project goal.")

    # new-lead
    p_lead = sub.add_parser("new-lead", help="Scaffold a new 5-zone research lead.")
    p_lead.add_argument("project_id", help="Parent project slug.")
    p_lead.add_argument("lead_id", help="Lead slug (e.g. 001-symplectic-drift).")
    p_lead.add_argument("--title", required=True, help="Human-readable lead title.")
    p_lead.add_argument(
        "--kind",
        choices=[k.value for k in LeadKind],
        default=LeadKind.HYBRID.value,
        help="Primary modality of this lead.",
    )

    # set-status
    p_set = sub.add_parser("set-status", help="Update a lead's lifecycle/verdict status.")
    p_set.add_argument("lead", help="Lead path or <project>/<lead>.")
    p_set.add_argument("status", choices=[s.value for s in LeadStatus])

    # run
    p_run = sub.add_parser("run", help="Run a command inside a lead with provenance capture.")
    p_run.add_argument("lead", help="Lead path or <project>/<lead>.")
    p_run.add_argument("--seed", type=int, default=42, help="Deterministic seed (RPIPE_SEED).")
    p_run.add_argument("--timeout", type=int, default=300, help="Timeout in seconds.")
    p_run.add_argument("--tag", default=None, help="Optional short run label.")
    p_run.add_argument("--json", action="store_true", help="Emit manifest JSON.")

    # verify
    p_ver = sub.add_parser("verify", help="Run multi-layer scientific verification for a lead.")
    p_ver.add_argument("lead", help="Lead path or <project>/<lead>.")
    p_ver.add_argument(
        "--require-lean",
        action="store_true",
        help="Fail if declared .lean files cannot compile because `lean` is absent.",
    )
    p_ver.add_argument("--json", action="store_true", help="Emit report JSON.")

    return parser


def _split_run_argv(raw_argv: list[str]) -> tuple[list[str], list[str]]:
    """Split `rpipe run ... [--] <cmd...>` cleanly even if a shell strips `--`."""
    if not raw_argv or raw_argv[0] != "run":
        return raw_argv, []

    value_flags = {"--seed", "--timeout", "--tag"}
    bool_flags = {"--json", "-h", "--help"}

    head: list[str] = ["run"]
    i = 1
    seen_lead = False
    while i < len(raw_argv):
        tok = raw_argv[i]
        if tok == "--":
            return head, raw_argv[i + 1 :]
        if tok in value_flags:
            head.append(tok)
            if i + 1 < len(raw_argv):
                head.append(raw_argv[i + 1])
                i += 2
            else:
                i += 1
            continue
        if any(tok.startswith(f"{flag}=") for flag in value_flags) or tok in bool_flags:
            head.append(tok)
            i += 1
            continue
        if not seen_lead and not tok.startswith("-"):
            head.append(tok)
            seen_lead = True
            i += 1
            continue
        return head, raw_argv[i:]
    return head, []


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    parse_argv, run_cmd = _split_run_argv(raw_argv)
    args = parser.parse_args(parse_argv)

    if args.subcommand == "status":
        data = workspace_status(project_filter=args.project)
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            _print_status_human(data)
        return 0

    if args.subcommand == "init-project":
        path = init_project(args.project_id, title=args.title, summary=args.summary)
        print(f"Created project: {path.as_posix()}")
        return 0

    if args.subcommand == "new-lead":
        path = new_lead(
            args.project_id,
            args.lead_id,
            title=args.title,
            kind=LeadKind(args.kind),
        )
        print(f"Created lead: {path.as_posix()}")
        return 0

    if args.subcommand == "set-status":
        lead_dir = resolve_lead_dir(args.lead)
        spec = set_lead_status(lead_dir, LeadStatus(args.status))
        print(f"{spec.project}/{spec.id} -> {spec.status.value}")
        return 0

    if args.subcommand == "run":
        cmd = list(run_cmd)
        if not cmd:
            parser.error("Provide a command to execute, e.g. `-- python work/sim.py`.")
        lead_dir = resolve_lead_dir(args.lead)
        manifest = run_in_lead(
            lead_dir,
            cmd,
            seed=args.seed,
            timeout_sec=args.timeout,
            tag=args.tag,
        )
        if args.json:
            print(manifest.model_dump_json(indent=2))
        else:
            print(
                f"Run {manifest.run_id} finished (exit={manifest.exit_code}, "
                f"duration={manifest.duration_sec}s, dir={manifest.run_dir})"
            )
            if manifest.summary is not None:
                print("Summary:", json.dumps(manifest.summary, indent=2))
        return 0 if manifest.exit_code == 0 else manifest.exit_code

    if args.subcommand == "verify":
        lead_dir = resolve_lead_dir(args.lead)
        report = verify_lead(lead_dir, require_lean=args.require_lean)
        if args.json:
            print(report.model_dump_json(indent=2))
        else:
            verdict = "PASS" if report.passed else "FAIL"
            print(f"Verification [{verdict}] for {report.project_id}/{report.lead_id}")
            for outcome in report.outcomes:
                first_line = outcome.message.splitlines()[0] if outcome.message else ""
                print(
                    f"  - [{outcome.status.upper():7s}] {outcome.name} "
                    f"({outcome.kind}, {outcome.duration_sec}s): {first_line}"
                )
        return 0 if report.passed else 1

    return 2


if __name__ == "__main__":
    sys.exit(main())
