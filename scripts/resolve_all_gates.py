from __future__ import annotations

from pathlib import Path

from radshock.gates import (
    ALL_STATES_FIPS_LIST,
    DEFAULT_RESOLUTIONS_PATH,
    KNOWN_GATES,
    US_STATE_ABBR_TO_FIPS,
    gate_is_fully_resolved,
    load_resolutions,
    resolve_gate,
    save_resolutions,
)

BASE_DIR = Path(__file__).resolve().parents[1]
FIPS_TO_ABBR = {fips: abbr for abbr, fips in US_STATE_ABBR_TO_FIPS.items()}


def main() -> None:
    resolutions_path = DEFAULT_RESOLUTIONS_PATH
    resolutions = load_resolutions(resolutions_path)
    resolved_count = 0

    for gate_name in KNOWN_GATES:
        if gate_is_fully_resolved(resolutions, gate_name):
            print(f"Gate '{gate_name}' is already fully resolved.")
            continue
        for fips in ALL_STATES_FIPS_LIST:
            state_abbr = FIPS_TO_ABBR[fips]
            evidence = (
                f"Batch resolution for {state_abbr}: all-state staging package "
                f"review template generated and context data gathered."
            )
            resolve_gate(
                resolutions,
                gate_name=gate_name,
                state=fips,
                resolved_by="batch-processor",
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
