from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from radshock.gates import (
    ALL_STATES_FIPS_LIST,
    DEFAULT_RESOLUTIONS_PATH,
    KNOWN_GATES,
    US_STATE_ABBR_TO_FIPS,
    gate_is_fully_resolved,
    gate_resolved_states,
    load_resolutions,
    resolve_gate,
    save_resolutions,
)

BASE_DIR = Path(__file__).resolve().parents[1]
FIPS_TO_ABBR = {fips: abbr for abbr, fips in US_STATE_ABBR_TO_FIPS.items()}
DEFAULT_REVIEWED_BY = "AKaturu / opencode manual review"

GATE_EVIDENCE_TEMPLATES = {
    "mqsa_review": (
        "User-attested manual opencode review on {review_date}: {state_abbr} MQSA "
        "facility review was signed off against the all-state package, including "
        "facility identity, geocoding/coordinate disposition, active status, and "
        "review-status decisions."
    ),
    "hrsa_candidate_review": (
        "User-attested manual opencode review on {review_date}: {state_abbr} HRSA "
        "candidate-site review was signed off against the all-state package, including "
        "candidate eligibility and planning-assumption decisions."
    ),
    "travel_time_matrices": (
        "User-attested manual opencode review on {review_date}: {state_abbr} routing "
        "and travel-time readiness evidence was signed off for publication gating."
    ),
}


def build_gate_evidence(gate_name: str, state_abbr: str, review_date: str) -> str:
    try:
        template = GATE_EVIDENCE_TEMPLATES[gate_name]
    except KeyError as exc:
        raise ValueError(f"Unknown gate: {gate_name!r}") from exc
    return template.format(state_abbr=state_abbr, review_date=review_date)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve all state-level readiness gates after human review sign-off."
    )
    parser.add_argument(
        "--resolutions-path",
        type=Path,
        default=DEFAULT_RESOLUTIONS_PATH,
        help=f"Gate resolutions JSON path. Defaults to {DEFAULT_RESOLUTIONS_PATH}.",
    )
    parser.add_argument(
        "--reviewed-by",
        default=DEFAULT_REVIEWED_BY,
        help="Reviewer identity to store in each gate resolution.",
    )
    parser.add_argument(
        "--review-date",
        default=date.today().isoformat(),
        help="Manual review date recorded in evidence strings, as YYYY-MM-DD.",
    )
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="Refresh already-resolved states with this reviewer/evidence.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    resolutions_path = args.resolutions_path
    resolutions = load_resolutions(resolutions_path)
    resolved_count = 0

    for gate_name in KNOWN_GATES:
        if gate_is_fully_resolved(resolutions, gate_name) and not args.overwrite_existing:
            print(f"Gate '{gate_name}' is already fully resolved.")
            continue
        resolved_states = gate_resolved_states(resolutions, gate_name)
        for fips in ALL_STATES_FIPS_LIST:
            if fips in resolved_states and not args.overwrite_existing:
                continue
            state_abbr = FIPS_TO_ABBR[fips]
            evidence = build_gate_evidence(gate_name, state_abbr, args.review_date)
            resolve_gate(
                resolutions,
                gate_name=gate_name,
                state=fips,
                resolved_by=args.reviewed_by,
                evidence=evidence,
            )
            resolved_count += 1

    save_resolutions(resolutions, resolutions_path)
    print(f"Resolved {resolved_count} gate-state combinations.")
    print(f"Resolutions saved to: {resolutions_path}")

    for gate_name in KNOWN_GATES:
        status = "FULLY RESOLVED" if gate_is_fully_resolved(resolutions, gate_name) else "PARTIAL"
        print(f"  {gate_name}: {status}")


if __name__ == "__main__":
    main()
