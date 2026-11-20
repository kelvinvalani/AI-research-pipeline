"""Tests for rpipe schemas."""

from __future__ import annotations

from rpipe.schemas import LeadKind, LeadSpec, LeadStatus, ProjectMeta


def test_lead_spec_defaults_and_roundtrip() -> None:
    spec = LeadSpec(id="001-test", project="demo", title="Demo Lead")
    assert spec.kind == LeadKind.HYBRID
    assert spec.status == LeadStatus.EXPLORING
    dumped = spec.model_dump(mode="json")
    loaded = LeadSpec.model_validate(dumped)
    assert loaded == spec


def test_project_meta_validation() -> None:
    meta = ProjectMeta(id="demo", title="Demo Project", summary="Test summary")
    assert meta.status == "active"
    assert meta.domain == "physics-math"
