from __future__ import annotations

from pathlib import Path

import pytest

from radshock.gates import (
    KNOWN_GATES,
    GateResolutions,
    load_gate_resolutions,
    save_gate_resolutions,
)


def test_gate_resolutions_empty() -> None:
    r = GateResolutions()
    assert r.resolved_count() == 0
    assert r.total_state_gate_pairs() > 0


def test_resolve_and_is_resolved() -> None:
    r = GateResolutions()
    r.resolve("mqsa_review", "NC", "evidence-1")
    assert r.is_resolved("mqsa_review", "NC")
    assert not r.is_resolved("mqsa_review", "VA")
    assert not r.is_resolved("hrsa_candidate_review", "NC")


def test_resolve_duplicate_raises() -> None:
    r = GateResolutions()
    r.resolve("mqsa_review", "NC", "evidence-1")
    with pytest.raises(ValueError):
        r.resolve("mqsa_review", "NC", "evidence-2")


def test_unresolve() -> None:
    r = GateResolutions()
    r.resolve("mqsa_review", "NC", "e1")
    r.unresolve("mqsa_review", "NC")
    assert not r.is_resolved("mqsa_review", "NC")


def test_unresolve_not_resolved_raises() -> None:
    r = GateResolutions()
    with pytest.raises(ValueError):
        r.unresolve("mqsa_review", "NC")


def test_unresolved_states() -> None:
    r = GateResolutions()
    unresolved = r.unresolved_states("mqsa_review")
    assert "NC" in unresolved
    assert "PR" not in unresolved  # PR is excluded


def test_state_summary() -> None:
    r = GateResolutions()
    r.resolve("mqsa_review", "NC", "e1")
    summary = r.state_summary("NC")
    assert summary["mqsa_review"] is True
    assert summary["hrsa_candidate_review"] is False
    assert summary["travel_time_matrices"] is False


def test_active_gates() -> None:
    r = GateResolutions()
    gates = r.active_gates()
    assert len(gates) == len(KNOWN_GATES)
    for g in gates:
        assert g["resolved_states"] == 0


def test_save_and_load(tmp_path: Path) -> None:
    path = tmp_path / "resolutions.json"
    r = GateResolutions()
    r.resolve("mqsa_review", "NC", "test-evidence")
    save_gate_resolutions(path, r)
    loaded = load_gate_resolutions(path)
    assert loaded.is_resolved("mqsa_review", "NC")
    assert loaded.resolved_count() == 1


def test_load_missing_file_returns_empty() -> None:
    r = load_gate_resolutions(Path("/nonexistent/resolutions.json"))
    assert r.resolved_count() == 0


def test_resolution_sets_resolved_at() -> None:
    r = GateResolutions()
    resolution = r.resolve("travel_time_matrices", "NC", "evidence")
    assert resolution.resolved_at is not None
    assert resolution.resolved_by == "cli"


def test_resolution_with_custom_resolved_by() -> None:
    r = GateResolutions()
    resolution = r.resolve(
        "travel_time_matrices", "NC", "evidence", resolved_by="ci"
    )
    assert resolution.resolved_by == "ci"
