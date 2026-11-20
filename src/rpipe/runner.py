"""Reproducible subprocess execution with provenance manifests and pluggable executor seam."""

from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from rpipe.schemas import RunManifest, utc_now_iso
from rpipe.workspace import find_repo_root, load_lead


class Executor(Protocol):
    """Minimal seam for future compute backends (e.g. Slurm, Ray, Docker)."""

    name: str

    def execute(
        self,
        lead_dir: Path,
        command: list[str],
        *,
        seed: int = 42,
        timeout_sec: int = 300,
        tag: str | None = None,
    ) -> RunManifest: ...


def _git_info(repo_root: Path) -> tuple[str | None, bool | None]:
    try:
        sha_proc = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        sha = sha_proc.stdout.strip() if sha_proc.returncode == 0 else None
        status_proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        dirty = bool(status_proc.stdout.strip()) if status_proc.returncode == 0 else None
        return sha, dirty
    except (OSError, subprocess.SubprocessError):
        return None, None


def normalize_command(command: list[str]) -> list[str]:
    """Ensure bare `python` / `python3` invokes the active virtual environment interpreter."""
    if not command:
        raise ValueError("Command cannot be empty.")
    head = command[0]
    if head in ("python", "python3"):
        return [sys.executable, *command[1:]]
    return list(command)


def _make_run_id(tag: str | None) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    if not tag:
        return stamp
    clean_tag = re.sub(r"[^a-zA-Z0-9_-]+", "-", tag).strip("-")[:32]
    return f"{stamp}_{clean_tag}" if clean_tag else stamp


class LocalExecutor:
    """Runs commands in an isolated local subprocess with deterministic seed & manifest capture."""

    name = "local"

    def execute(
        self,
        lead_dir: Path,
        command: list[str],
        *,
        seed: int = 42,
        timeout_sec: int = 300,
        tag: str | None = None,
    ) -> RunManifest:
        spec = load_lead(lead_dir)
        repo_root = find_repo_root(lead_dir)
        runs_root = lead_dir / "runs"
        runs_root.mkdir(parents=True, exist_ok=True)

        base_run_id = _make_run_id(tag)
        run_id = base_run_id
        suffix = 1
        while (runs_root / run_id).exists():
            suffix += 1
            run_id = f"{base_run_id}_{suffix}"

        run_dir = runs_root / run_id
        run_dir.mkdir(parents=True, exist_ok=False)

        resolved_cmd = normalize_command(command)
        env = os.environ.copy()
        env["RPIPE_RUN_DIR"] = str(run_dir.resolve())
        env["RPIPE_LEAD_DIR"] = str(lead_dir.resolve())
        env["RPIPE_REPO_ROOT"] = str(repo_root.resolve())
        existing_py = env.get("PYTHONPATH", "")
        lead_str = str(lead_dir.resolve())
        env["PYTHONPATH"] = f"{lead_str}{os.pathsep}{existing_py}" if existing_py else lead_str
        env["RPIPE_SEED"] = str(seed)
        env["PYTHONHASHSEED"] = str(seed)
        env["PYTHONUTF8"] = "1"
        env.setdefault("MPLBACKEND", "Agg")

        started_at = utc_now_iso()
        t0 = time.perf_counter()
        timed_out = False
        exit_code = -1
        stdout_text = ""
        stderr_text = ""

        try:
            proc = subprocess.run(
                resolved_cmd,
                cwd=lead_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                check=False,
            )
            exit_code = proc.returncode
            stdout_text = proc.stdout
            stderr_text = proc.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            exit_code = 124
            stdout_text = (
                exc.stdout.decode("utf-8", errors="replace")
                if isinstance(exc.stdout, bytes)
                else (exc.stdout or "")
            )
            stderr_text = (
                exc.stderr.decode("utf-8", errors="replace")
                if isinstance(exc.stderr, bytes)
                else (exc.stderr or "")
            ) + f"\n[rpipe] Command timed out after {timeout_sec}s.\n"

        duration_sec = round(time.perf_counter() - t0, 4)
        finished_at = utc_now_iso()

        (run_dir / "stdout.log").write_text(stdout_text, encoding="utf-8")
        (run_dir / "stderr.log").write_text(stderr_text, encoding="utf-8")

        summary_path = run_dir / "summary.json"
        summary_data = None
        summary_rel = None
        if summary_path.exists():
            try:
                summary_data = json.loads(summary_path.read_text(encoding="utf-8"))
                summary_rel = "summary.json"
            except json.JSONDecodeError:
                summary_data = {"_error": "Invalid JSON in summary.json"}

        git_sha, git_dirty = _git_info(repo_root)
        manifest = RunManifest(
            run_id=run_id,
            lead_id=spec.id,
            project_id=spec.project,
            tag=tag,
            command=command,
            seed=seed,
            executor=self.name,
            started_at=started_at,
            finished_at=finished_at,
            duration_sec=duration_sec,
            exit_code=exit_code,
            timed_out=timed_out,
            git_sha=git_sha,
            git_dirty=git_dirty,
            python_version=platform.python_version(),
            run_dir=str(run_dir.relative_to(lead_dir).as_posix()),
            summary_file=summary_rel,
            summary=summary_data,
        )

        (run_dir / "manifest.json").write_text(
            manifest.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )
        with (runs_root / "ledger.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(manifest.model_dump_json() + "\n")

        return manifest


def run_in_lead(
    lead_dir: Path,
    command: list[str],
    *,
    seed: int = 42,
    timeout_sec: int = 300,
    tag: str | None = None,
    executor: Executor | None = None,
) -> RunManifest:
    """Execute a command inside `lead_dir` using the configured executor."""
    active_executor = executor or LocalExecutor()
    return active_executor.execute(
        lead_dir,
        command,
        seed=seed,
        timeout_sec=timeout_sec,
        tag=tag,
    )
