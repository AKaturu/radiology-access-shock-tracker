from __future__ import annotations

from pathlib import Path

import pytest

from radshock.gates import (
    ALL_STATES_FIPS_LIST,
    KNOWN_GATES,
    RESOLUTIONS_FILE_VERSION,
    gate_is_fully_resolved,
    gate_resolved_states,
    get_active_gate_strings,
    get_state_gate_status,
    load_resolutions,
    resolve_gate,
    save_resolutions,
    unresolve_gate,
)


def test_default_resolutions_empty() -> None:
    resolutions = load_resolutions(Path("nonexistent.json"))
    assert resolutions["version"] == RESOLUTIONS_FILE_VERSION
    assert set(resolutions["gates"]) == set(KNOWN_GATES)
    for gate in KNOWN_GATES:
        assert resolutions["gates"][gate]["resolved_states"] == {}


def test_resolve_and_save_load(tmp_path: Path) -> None:
    p = tmp_path / "resolutions.json"
    resolutions = load_resolutions(p)
    resolve_gate(
        resolutions,
        gate_name="mqsa_review",
        state="NC",
        resolved_by="@test",
        evidence="test evidence",
    )
    save_resolutions(resolutions, p)

    loaded = load_resolutions(p)
    assert loaded["gates"]["mqsa_review"]["resolved_states"]["37"]["resolved_by"] == "@test"
    assert loaded["gates"]["mqsa_review"]["resolved_states"]["37"]["evidence"] == "test evidence"


def test_resolve_gate_unknown_gate() -> None:
    resolutions = load_resolutions(Path("nonexistent.json"))
    with pytest.raises(ValueError, match="Unknown gate"):
        resolve_gate(
            resolutions,
            gate_name="nonexistent",
            state="NC",
            resolved_by="@x",
            evidence="x",
        )


def test_resolve_gate_unknown_state() -> None:
    resolutions = load_resolutions(Path("nonexistent.json"))
    with pytest.raises(ValueError, match="Unknown state"):
        resolve_gate(
            resolutions,
            gate_name="mqsa_review",
            state="XX",
            resolved_by="@x",
            evidence="x",
        )


def test_resolve_and_unresolve(tmp_path: Path) -> None:
    p = tmp_path / "resolutions.json"
    resolutions = load_resolutions(p)
    resolve_gate(
        resolutions,
        gate_name="hrsa_candidate_review",
        state="CA",
        resolved_by="@tester",
        evidence="review done",
    )
    assert "06" in gate_resolved_states(resolutions, "hrsa_candidate_review")

    unresolve_gate(resolutions, gate_name="hrsa_candidate_review", state="CA")
    assert "06" not in gate_resolved_states(resolutions, "hrsa_candidate_review")


def test_gate_is_fully_resolved(tmp_path: Path) -> None:
    p = tmp_path / "resolutions.json"
    resolutions = load_resolutions(p)

    assert not gate_is_fully_resolved(resolutions, "mqsa_review")

    for fips in ALL_STATES_FIPS_LIST:
        resolve_gate(
            resolutions,
            gate_name="mqsa_review",
            state=fips,
            resolved_by="@test",
            evidence="bulk",
        )

    assert gate_is_fully_resolved(resolutions, "mqsa_review")


def test_get_active_gate_strings_all_active(tmp_path: Path) -> None:
    p = tmp_path / "resolutions.json"
    resolutions = load_resolutions(p)

    active = get_active_gate_strings(resolutions)
    assert len(active) == 3


def test_get_active_gate_strings_partially_resolved(tmp_path: Path) -> None:
    p = tmp_path / "resolutions.json"
    resolutions = load_resolutions(p)
    resolve_gate(
        resolutions,
        gate_name="travel_time_matrices",
        state="NC",
        resolved_by="@test",
        evidence="done",
    )

    active = get_active_gate_strings(resolutions)
    travel_time_gates = [g for g in active if "Travel-time" in g]
    assert len(travel_time_gates) == 1
    assert "50 of 51" in travel_time_gates[0]


def test_get_active_gate_strings_one_fully_resolved(tmp_path: Path) -> None:
    p = tmp_path / "resolutions.json"
    resolutions = load_resolutions(p)

    for fips in ALL_STATES_FIPS_LIST:
        resolve_gate(
            resolutions,
            gate_name="mqsa_review",
            state=fips,
            resolved_by="@test",
            evidence="bulk",
        )

    active = get_active_gate_strings(resolutions)
    mqsa_gates = [g for g in active if "MQSA" in g]
    assert len(mqsa_gates) == 0
    assert len(active) == 2


def test_get_state_gate_status(tmp_path: Path) -> None:
    p = tmp_path / "resolutions.json"
    resolutions = load_resolutions(p)
    resolve_gate(
        resolutions,
        gate_name="mqsa_review",
        state="NC",
        resolved_by="@user",
        evidence="evidence path",
    )

    status = get_state_gate_status(resolutions, "NC")
    assert status["mqsa_review"]["status"] == "RESOLVED"
    assert status["hrsa_candidate_review"]["status"] == "UNRESOLVED"
    assert status["travel_time_matrices"]["status"] == "UNRESOLVED"


def test_get_state_gate_status_with_fips(tmp_path: Path) -> None:
    p = tmp_path / "resolutions.json"
    resolutions = load_resolutions(p)
    resolve_gate(
        resolutions,
        gate_name="travel_time_matrices",
        state="37",
        resolved_by="@user",
        evidence="routing done",
    )

    status = get_state_gate_status(resolutions, "NC")
    assert status["travel_time_matrices"]["status"] == "RESOLVED"
    assert status["travel_time_matrices"]["evidence"] == "routing done"
