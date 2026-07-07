from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from radshock.states import US_STATE_ABBR_TO_FIPS

GateName = Literal["mqsa_review", "hrsa_candidate_review", "travel_time_matrices"]

GATE_METADATA: dict[str, dict[str, str]] = {
    "mqsa_review": {
        "label": "MQSA review",
        "description": (
            "MQSA rows are review templates; coordinates, active status, and "
            "review_status require approval."
        ),
    },
    "hrsa_candidate_review": {
        "label": "HRSA candidate review",
        "description": (
            "HRSA rows are planning candidates; mammography capability is not "
            "claimed until candidate review is approved."
        ),
    },
    "travel_time_matrices": {
        "label": "Travel-time matrices",
        "description": (
            "Travel-time matrices are not generated for this all-state staging package."
        ),
    },
}

KNOWN_GATES: list[str] = list(GATE_METADATA.keys())

RESOLUTIONS_FILE_VERSION = 1

DEFAULT_RESOLUTIONS_PATH = Path("work/gate_resolutions.json")

ALL_STATES_FIPS_LIST: list[str] = sorted(US_STATE_ABBR_TO_FIPS.values())


def _empty_resolutions() -> dict[str, Any]:
    return {
        "version": RESOLUTIONS_FILE_VERSION,
        "gates": {
            name: {
                "label": meta["label"],
                "resolved_states": {},
            }
            for name, meta in GATE_METADATA.items()
        },
    }


def load_resolutions(path: Path | None = None) -> dict[str, Any]:
    resolved_path = path or DEFAULT_RESOLUTIONS_PATH
    if not resolved_path.exists():
        return _empty_resolutions()
    payload = json.loads(resolved_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("gates"), dict):
        return _empty_resolutions()
    result = _empty_resolutions()
    for gate_name, gate_spec in payload.get("gates", {}).items():
        if gate_name in KNOWN_GATES and isinstance(gate_spec, dict):
            states = gate_spec.get("resolved_states", {})
            if isinstance(states, dict):
                result["gates"][gate_name] = {
                    "label": GATE_METADATA[gate_name]["label"],
                    "resolved_states": {
                        str(fips): entry
                        for fips, entry in states.items()
                        if isinstance(entry, dict)
                    },
                }
    return result


def save_resolutions(
    resolutions: dict[str, Any],
    path: Path | None = None,
) -> None:
    resolved_path = path or DEFAULT_RESOLUTIONS_PATH
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path.write_text(
        json.dumps(resolutions, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


NumericFips = str


def _resolve_fips(state: str) -> str:
    raw = state.strip().upper()
    if raw in US_STATE_ABBR_TO_FIPS:
        return US_STATE_ABBR_TO_FIPS[raw]
    if raw in set(US_STATE_ABBR_TO_FIPS.values()):
        return raw
    raise ValueError(
        f"Unknown state: {state!r}. Use a 2-letter USPS abbreviation or 2-digit FIPS code."
    )


def resolve_gate(
    resolutions: dict[str, Any],
    *,
    gate_name: str,
    state: str,
    resolved_by: str,
    evidence: str,
) -> dict[str, Any]:
    if gate_name not in KNOWN_GATES:
        raise ValueError(f"Unknown gate: {gate_name!r}. Known gates: {KNOWN_GATES}")
    fips = _resolve_fips(state)
    gates = resolutions.setdefault("gates", {})
    gate_entry = gates.setdefault(
        gate_name,
        {"label": GATE_METADATA[gate_name]["label"], "resolved_states": {}},
    )
    states_entry = gate_entry.setdefault("resolved_states", {})
    states_entry[fips] = {
        "resolved_by": resolved_by,
        "resolved_at": datetime.now(UTC).isoformat(),
        "evidence": evidence,
    }
    return resolutions


def unresolve_gate(
    resolutions: dict[str, Any],
    *,
    gate_name: str,
    state: str,
) -> dict[str, Any]:
    if gate_name not in KNOWN_GATES:
        raise ValueError(f"Unknown gate: {gate_name!r}. Known gates: {KNOWN_GATES}")
    fips = _resolve_fips(state)
    gates = resolutions.get("gates", {})
    gate_entry = gates.get(gate_name)
    if gate_entry is None:
        return resolutions
    states_entry = gate_entry.get("resolved_states", {})
    states_entry.pop(fips, None)
    return resolutions


def gate_resolved_states(resolutions: dict[str, Any], gate_name: str) -> set[str]:
    gates = resolutions.get("gates", {})
    gate_entry = gates.get(gate_name, {})
    states = gate_entry.get("resolved_states", {})
    return set(states.keys()) if isinstance(states, dict) else set()


def gate_is_fully_resolved(resolutions: dict[str, Any], gate_name: str) -> bool:
    if gate_name not in KNOWN_GATES:
        return False
    resolved = gate_resolved_states(resolutions, gate_name)
    return resolved.issuperset(ALL_STATES_FIPS_LIST)


def get_active_gate_strings(resolutions: dict[str, Any]) -> list[str]:
    active: list[str] = []
    for gate_name in KNOWN_GATES:
        if not gate_is_fully_resolved(resolutions, gate_name):
            meta = GATE_METADATA.get(gate_name, {})
            resolved = gate_resolved_states(resolutions, gate_name)
            desc = meta.get("description", gate_name)
            if resolved:
                remaining = len(ALL_STATES_FIPS_LIST) - len(resolved)
                total = len(ALL_STATES_FIPS_LIST)
                active.append(
                    f"{desc} ({remaining} of {total} states remain unresolved.)"
                )
            else:
                active.append(desc)
    return active


def get_state_gate_status(
    resolutions: dict[str, Any],
    state: str,
) -> dict[str, dict[str, str | None]]:
    fips = _resolve_fips(state)
    result: dict[str, dict[str, str | None]] = {}
    for gate_name in KNOWN_GATES:
        entry = _get_resolved_entry(resolutions, gate_name, fips)
        if entry is not None:
            result[gate_name] = {
                "status": "RESOLVED",
                "resolved_by": str(entry.get("resolved_by", "")),
                "resolved_at": str(entry.get("resolved_at", "")),
                "evidence": str(entry.get("evidence", "")),
            }
        else:
            result[gate_name] = {"status": "UNRESOLVED"}
    return result


def _get_resolved_entry(
    resolutions: dict[str, Any], gate_name: str, fips: str
) -> dict[str, Any] | None:
    gates = resolutions.get("gates", {})
    if not isinstance(gates, dict):
        return None
    gate_entry = gates.get(gate_name, {})
    if not isinstance(gate_entry, dict):
        return None
    states_entry = gate_entry.get("resolved_states", {})
    if not isinstance(states_entry, dict):
        return None
    entry = states_entry.get(fips)
    return entry if isinstance(entry, dict) else None
