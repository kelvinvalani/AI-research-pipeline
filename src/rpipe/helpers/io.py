"""LLM-friendly output helpers for saving compact run summaries and metrics."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def get_run_dir(default: str | Path = ".") -> Path:
    """Return the active run directory (`RPIPE_RUN_DIR`) or `default` when run standalone."""
    raw = os.environ.get("RPIPE_RUN_DIR")
    path = Path(raw) if raw else Path(default)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_seed(default: int = 42) -> int:
    """Return the deterministic seed set by `rpipe run` (`RPIPE_SEED`) or `default`."""
    raw = os.environ.get("RPIPE_SEED")
    return int(raw) if raw is not None else default


def save_summary(data: dict[str, Any], run_dir: Path | None = None) -> Path:
    """Write a compact JSON summary readable by LLMs and recorded in `manifest.json`."""
    target_dir = run_dir or get_run_dir()
    out_path = target_dir / "summary.json"
    out_path.write_text(
        json.dumps(data, indent=2, sort_keys=False, default=str) + "\n",
        encoding="utf-8",
    )
    return out_path


def log_metric(record: dict[str, Any], run_dir: Path | None = None) -> Path:
    """Append a single JSONL metric row to `metrics.jsonl` inside the run directory."""
    target_dir = run_dir or get_run_dir()
    out_path = target_dir / "metrics.jsonl"
    with out_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, default=str) + "\n")
    return out_path
