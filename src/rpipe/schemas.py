"""Pydantic schemas for projects, leads, runs, and verification reports."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class LeadKind(StrEnum):
    NUMERICAL = "numerical"
    SYMBOLIC = "symbolic"
    FORMAL = "formal"
    HYBRID = "hybrid"
    THEORETICAL = "theoretical"


class LeadStatus(StrEnum):
    EXPLORING = "exploring"
    PLANNED = "planned"
    RUNNING = "running"
    VERIFIED = "verified"
    CONFIRMED = "confirmed"
    FALSIFIED = "falsified"
    INCONCLUSIVE = "inconclusive"
    PARKED = "parked"


class ProjectMeta(BaseModel):
    id: str
    title: str
    summary: str = ""
    domain: str = "physics-math"
    status: str = "active"
    created_at: str = Field(default_factory=utc_now_iso)
    tags: list[str] = Field(default_factory=list)


class CheckSpec(BaseModel):
    name: str
    command: list[str]
    timeout_sec: int = 120


class VerificationConfig(BaseModel):
    pytest: bool = True
    lean_files: list[str] = Field(default_factory=list)
    checks: list[CheckSpec] = Field(default_factory=list)


class LeadLinks(BaseModel):
    parent_lead: str | None = None
    follow_up_leads: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)


class LeadSpec(BaseModel):
    id: str
    project: str
    title: str
    kind: LeadKind = LeadKind.HYBRID
    status: LeadStatus = LeadStatus.EXPLORING
    created_at: str = Field(default_factory=utc_now_iso)
    idea: str = ""
    mathematical_formulation: str = ""
    assumptions: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    falsification_criteria: list[str] = Field(default_factory=list)
    artifacts_planned: list[str] = Field(default_factory=list)
    verification: VerificationConfig = Field(default_factory=VerificationConfig)
    links: LeadLinks = Field(default_factory=LeadLinks)


class RunManifest(BaseModel):
    run_id: str
    lead_id: str
    project_id: str
    tag: str | None = None
    command: list[str]
    seed: int
    executor: str = "local"
    started_at: str
    finished_at: str
    duration_sec: float
    exit_code: int
    timed_out: bool = False
    git_sha: str | None = None
    git_dirty: bool | None = None
    python_version: str
    run_dir: str
    summary_file: str | None = None
    summary: dict[str, Any] | None = None


class CheckOutcome(BaseModel):
    name: str
    kind: str  # schema | pytest | custom | lean_audit | lean_compile
    status: str  # passed | failed | skipped
    duration_sec: float = 0.0
    message: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class VerificationReport(BaseModel):
    lead_id: str
    project_id: str
    checked_at: str = Field(default_factory=utc_now_iso)
    passed: bool
    outcomes: list[CheckOutcome] = Field(default_factory=list)
