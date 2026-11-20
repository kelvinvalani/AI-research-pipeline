"""Tests for inbox discovery, project refs scaffolding, and reference inspection."""

from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfWriter

from rpipe.refs import inspect_reference, list_inbox_files, parse_page_spec
from rpipe.workspace import init_project, workspace_status


def test_parse_page_spec() -> None:
    assert parse_page_spec("1-3, 5, 10-12", total_pages=11) == [0, 1, 2, 4, 9, 10]


def test_inbox_files_detected_in_workspace_status(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / "templates" / "project" / "refs").mkdir(parents=True)
    (tmp_path / "templates" / "project" / "project.yaml").write_text(
        'id: "{{PROJECT_ID}}"\ntitle: "{{PROJECT_TITLE}}"\n', encoding="utf-8"
    )
    (tmp_path / "templates" / "project" / "README.md").write_text(
        "# {{PROJECT_TITLE}}\n", encoding="utf-8"
    )
    (tmp_path / "templates" / "project" / "refs" / "README.md").write_text(
        "# Refs\n", encoding="utf-8"
    )
    (tmp_path / "inbox").mkdir()
    (tmp_path / "inbox" / "README.md").write_text("# Inbox\n", encoding="utf-8")
    (tmp_path / "inbox" / "draft.tex").write_text(r"\section{Test}", encoding="utf-8")

    assert list_inbox_files(tmp_path) == ["inbox/draft.tex"]

    proj_dir = init_project("demo-proj", title="Demo Project", repo_root=tmp_path)
    assert (proj_dir / "refs" / "README.md").exists()

    status = workspace_status(repo_root=tmp_path)
    assert status["inbox_files"] == ["inbox/draft.tex"]


def test_inspect_reference_tex_ipynb_and_pdf(tmp_path: Path) -> None:
    # 1. LaTeX file
    tex = tmp_path / "notes.tex"
    tex.write_text(r"H = \frac{1}{2} p^2 + V(q)", encoding="utf-8")
    tex_info = inspect_reference(tex)
    assert tex_info["kind"] == "tex"
    assert r"\frac{1}{2}" in tex_info["content"]

    # 2. Jupyter notebook
    nb = tmp_path / "calc.ipynb"
    nb.write_text(
        json.dumps(
            {
                "cells": [
                    {"cell_type": "markdown", "source": ["# Heading\n"]},
                    {"cell_type": "code", "source": ["x = 42\n"]},
                ]
            }
        ),
        encoding="utf-8",
    )
    nb_info = inspect_reference(nb)
    assert nb_info["kind"] == "notebook"
    assert nb_info["total_cells"] == 2
    assert nb_info["content"][1]["source"] == "x = 42\n"

    # 3. Minimal PDF generated via pypdf
    pdf = tmp_path / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.add_blank_page(width=200, height=200)
    with pdf.open("wb") as fh:
        writer.write(fh)

    pdf_info = inspect_reference(pdf, pages="2")
    assert pdf_info["kind"] == "pdf"
    assert pdf_info["total_pages"] == 2
    assert pdf_info["pages_extracted"] == [2]
    assert any("sparse" in n for n in pdf_info["notes"])
