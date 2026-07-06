from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from radshock.data.states import STATE_FIPS_MAP

KNOWN_GATES = ["mqsa_review", "hrsa_candidate_review", "travel_time_matrices"]


@dataclass
class GateResolution:
    gate_name: str
    state: str
    resolved_at: str
    resolved_by: str
    evidence: str

    def to_dict(self) -> dict[str, str]:
        return {
            "gate_name": self.gate_name,
            "state": self.state,
            "resolved_at": self.resolved_at,
            "resolved_by": self.resolved_by,
            "evidence": self.evidence,
        }


@dataclass
class GateResolutions:
    resolutions: list[GateResolution] = field(default_factory=list)

    def is_resolved(self, gate_name: str, state: str) -> bool:
        return any(
            r.gate_name == gate_name and r.state == state.upper()
            for r in self.resolutions
        )

    def resolve(
        self,
        gate_name: str,
        state: str,
        evidence: str,
        resolved_by: str = "cli",
    ) -> GateResolution:
        if self.is_resolved(gate_name, state):
            raise ValueError(
                f"Gate '{gate_name}' for state '{state}' is already resolved."
            )
        resolution = GateResolution(
            gate_name=gate_name,
            state=state.upper(),
            resolved_at=datetime.now(UTC).isoformat(),
            resolved_by=resolved_by,
            evidence=evidence,
        )
        self.resolutions.append(resolution)
        return resolution

    def unresolve(self, gate_name: str, state: str) -> None:
        before = len(self.resolutions)
        self.resolutions = [
            r
            for r in self.resolutions
            if not (r.gate_name == gate_name and r.state == state.upper())
        ]
        if len(self.resolutions) == before:
            raise ValueError(
                f"Gate '{gate_name}' for state '{state}' is not resolved."
            )

    def unresolved_states(self, gate_name: str) -> list[str]:
        resolved = {r.state for r in self.resolutions if r.gate_name == gate_name}
        return sorted(
            abbr
            for abbr in STATE_FIPS_MAP
            if abbr not in resolved and abbr != "PR"
        )

    def state_summary(self, state: str) -> dict[str, bool]:
        state = state.upper()
        return {gate: self.is_resolved(gate, state) for gate in KNOWN_GATES}

    def total_state_gate_pairs(self) -> int:
        return len(KNOWN_GATES) * (len(STATE_FIPS_MAP) - 1)  # exclude PR

    def resolved_count(self) -> int:
        return len(self.resolutions)

    def active_gates(self) -> list[dict[str, Any]]:
        result = []
        for gate in KNOWN_GATES:
            unresolved = self.unresolved_states(gate)
            if unresolved:
                result.append({
                    "gate_name": gate,
                    "total_states": len(STATE_FIPS_MAP) - 1,
                    "resolved_states": (len(STATE_FIPS_MAP) - 1) - len(unresolved),
                    "unresolved_states": unresolved,
                })
        return result

    def to_dict(self) -> list[dict[str, str]]:
        return [r.to_dict() for r in self.resolutions]


def load_gate_resolutions(path: Path) -> GateResolutions:
    if not path.exists():
        return GateResolutions()
    data = json.loads(path.read_text(encoding="utf-8"))
    resolutions = [GateResolution(**item) for item in data]
    return GateResolutions(resolutions=resolutions)


def save_gate_resolutions(path: Path, resolutions: GateResolutions) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(resolutions.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
