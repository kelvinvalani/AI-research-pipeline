"""Lightweight reference inspection utilities (PDF, Jupyter notebooks, LaTeX, images, text)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff"}
TEXT_SUFFIXES = {
    ".tex",
    ".md",
    ".txt",
    ".bib",
    ".py",
    ".lean",
    ".yaml",
    ".yml",
    ".json",
    ".csv",
    ".tsv",
    ".rst",
    ".org",
}


def list_inbox_files(repo_root: Path) -> list[str]:
    """Return relative POSIX paths of non-README files currently waiting in `inbox/`."""
    inbox_dir = repo_root / "inbox"
    if not inbox_dir.exists():
        return []
    files: list[str] = []
    for path in sorted(inbox_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.name.lower() in {"readme.md", ".gitkeep"}:
            continue
        files.append(path.relative_to(repo_root).as_posix())
    return files


def parse_page_spec(spec: str, total_pages: int) -> list[int]:
    """Parse 1-indexed page ranges like `1-3,5,8-10` into sorted 0-indexed page numbers."""
    pages: set[int] = set()
    for chunk in spec.split(","):
        part = chunk.strip()
        if not part:
            continue
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start = max(1, int(start_s))
            end = min(total_pages, int(end_s))
            for p in range(start, end + 1):
                pages.add(p - 1)
        else:
            p = int(part)
            if 1 <= p <= total_pages:
                pages.add(p - 1)
    return sorted(pages)


def inspect_reference(
    path: Path,
    *,
    pages: str | None = None,
    max_chars: int = 20000,
) -> dict[str, Any]:
    """Inspect a reference file in a compact, LLM-friendly format across all IDEs."""
    target = path.resolve()
    if not target.exists() or not target.is_file():
        raise FileNotFoundError(f"Reference file not found: {path}")

    suffix = target.suffix.lower()
    size_bytes = target.stat().st_size

    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(target))
        total_pages = len(reader.pages)
        selected = (
            parse_page_spec(pages, total_pages)
            if pages
            else list(range(min(total_pages, 5)))
        )
        extracted_pages: list[dict[str, Any]] = []
        total_chars = 0
        truncated = False
        for idx in selected:
            raw_text = (reader.pages[idx].extract_text() or "").strip()
            remaining = max_chars - total_chars
            if remaining <= 0:
                truncated = True
                break
            if len(raw_text) > remaining:
                raw_text = raw_text[:remaining] + "\n...[truncated]"
                truncated = True
            total_chars += len(raw_text)
            extracted_pages.append({"page": idx + 1, "text": raw_text})

        avg_chars = (
            sum(len(p["text"]) for p in extracted_pages) / max(len(extracted_pages), 1)
        )
        notes = []
        if not pages and total_pages > 5:
            notes.append(
                f"Showing first 5 of {total_pages} pages. Pass `--pages 6-10` to inspect more."
            )
        if avg_chars < 80:
            notes.append(
                "Extracted text is sparse (possibly scanned or heavy math). "
                "Prefer native multimodal PDF/image viewing if your agent supports it."
            )
        return {
            "path": target.as_posix(),
            "kind": "pdf",
            "size_bytes": size_bytes,
            "total_pages": total_pages,
            "pages_extracted": [p["page"] for p in extracted_pages],
            "truncated": truncated,
            "notes": notes,
            "content": extracted_pages,
        }

    if suffix == ".ipynb":
        nb = json.loads(target.read_text(encoding="utf-8"))
        cells_out: list[dict[str, Any]] = []
        total_chars = 0
        truncated = False
        for idx, cell in enumerate(nb.get("cells", [])):
            source = "".join(cell.get("source", []))
            remaining = max_chars - total_chars
            if remaining <= 0:
                truncated = True
                break
            if len(source) > remaining:
                source = source[:remaining] + "\n...[truncated]"
                truncated = True
            total_chars += len(source)
            cells_out.append(
                {
                    "cell": idx,
                    "cell_type": cell.get("cell_type", "unknown"),
                    "source": source,
                }
            )
        return {
            "path": target.as_posix(),
            "kind": "notebook",
            "size_bytes": size_bytes,
            "total_cells": len(nb.get("cells", [])),
            "truncated": truncated,
            "content": cells_out,
        }

    if suffix in IMAGE_SUFFIXES:
        return {
            "path": target.as_posix(),
            "kind": "image",
            "size_bytes": size_bytes,
            "notes": [
                "Image file (e.g., whiteboard sketch, figure, or screenshot). "
                "Open directly with your multimodal file viewer to read equations/diagrams."
            ],
        }

    if suffix in TEXT_SUFFIXES:
        raw = target.read_text(encoding="utf-8", errors="replace")
        truncated = len(raw) > max_chars
        text = raw[:max_chars] + ("\n...[truncated]" if truncated else "")
        return {
            "path": target.as_posix(),
            "kind": suffix.lstrip("."),
            "size_bytes": size_bytes,
            "truncated": truncated,
            "content": text,
        }

    return {
        "path": target.as_posix(),
        "kind": "binary",
        "size_bytes": size_bytes,
        "notes": [
            f"Unsupported binary format '{suffix}'. Inspect with an appropriate domain tool."
        ],
    }
