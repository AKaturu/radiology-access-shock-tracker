from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from radshock.adapters.acs import (
    build_state_county_analysis_context,
    build_state_tract_analysis_context,
    to_analysis_counties,
    to_tract_population_points,
)
from radshock.data.states import STATE_FIPS_MAP
from radshock.gates import load_gate_resolutions


def main() -> None:
    args = _parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    api_key = args.api_key
    year = args.acs_year
    allow_missing_acs = args.allow_missing_acs
    res_file = Path(args.resolutions_file) if args.resolutions_file else None
    resolutions = load_gate_resolutions(res_file) if res_file else None

    all_counties: list[pd.DataFrame] = []
    all_tracts: list[pd.DataFrame] = []
    all_population_points: list[pd.DataFrame] = []
    state_summaries: dict[str, dict[str, int]] = {}
    failures: list[str] = []

    states = [s for s in STATE_FIPS_MAP if s != "PR"]

    for state_abbr in states:
        print(f"Processing {state_abbr}...")
        try:
            if api_key:
                county_ctx = build_state_county_analysis_context(
                    state_abbr, year=year, api_key=api_key, timeout=args.timeout
                )
                tract_ctx = build_state_tract_analysis_context(
                    state_abbr, year=year, api_key=api_key, timeout=args.timeout
                )
            elif allow_missing_acs:
                county_ctx = pd.DataFrame()
                tract_ctx = pd.DataFrame()
            else:
                print(f"  SKIP {state_abbr}: no API key and --allow-missing-acs not set")
                failures.append(f"{state_abbr} (missing API key)")
                state_summaries[state_abbr] = {"counties": 0, "tracts": 0, "population_points": 0}
                continue

            if not county_ctx.empty:
                counties = to_analysis_counties(county_ctx)
                all_counties.append(counties)
                pop_pts = to_tract_population_points(tract_ctx, include_zero_weight=False)
                all_population_points.append(pop_pts)
                all_tracts.append(tract_ctx)

                state_summaries[state_abbr] = {
                    "counties": len(counties),
                    "tracts": len(tract_ctx),
                    "population_points": len(pop_pts),
                }
                print(
                    f"  Counties: {len(counties)}, Tracts: {len(tract_ctx)}, "
                    f"Pop points: {len(pop_pts)}"
                )
            else:
                state_summaries[state_abbr] = {"counties": 0, "tracts": 0, "population_points": 0}
                failures.append(f"{state_abbr} (empty ACS)")
        except Exception as exc:
            print(f"  ERROR: {exc}")
            failures.append(f"{state_abbr} ({exc})")
            state_summaries[state_abbr] = {"counties": 0, "tracts": 0, "population_points": 0}

    if all_counties:
        combined_counties = pd.concat(all_counties, ignore_index=True)
        combined_counties.to_csv(output_dir / "counties.csv", index=False)
        print(f"Combined counties: {len(combined_counties)}")

    if all_tracts:
        combined_tracts = pd.concat(all_tracts, ignore_index=True)
        combined_tracts.to_csv(output_dir / "tract_context.csv", index=False)
        print(f"Combined tracts: {len(combined_tracts)}")

    if all_population_points:
        combined_pop = pd.concat(all_population_points, ignore_index=True)
        combined_pop.to_csv(output_dir / "population_points.csv", index=False)
        print(f"Combined population points: {len(combined_pop)}")

    _write_metadata(output_dir, year, state_summaries, failures, args)

    if resolutions is not None and args.mark_publication_ready:
        active = resolutions.active_gates()
        if active:
            gate_count = len(active)
            msg = (
                f"Cannot mark publication ready: {gate_count} gate(s) "
                "still have unresolved states."
            )
            for g in active:
                msg += f"\n  {g['gate_name']}: {len(g['unresolved_states'])} unresolved state(s)"
            raise RuntimeError(msg)
        print("All gates resolved; publication-ready check passed.")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build all-states data package with Census ACS and Gazetteer context."
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("work/all-states"),
        help="Output directory for the combined data package."
    )
    parser.add_argument(
        "--acs-year", type=int, default=2024,
        help="ACS/Gazetteer release year."
    )
    parser.add_argument(
        "--api-key", default=None,
        help="Census API key. Falls back to CENSUS_API_KEY env var."
    )
    parser.add_argument(
        "--timeout", type=int, default=60,
        help="HTTP timeout in seconds."
    )
    parser.add_argument(
        "--allow-missing-acs", action="store_true",
        help="Allow states with no ACS data to be included with empty context."
    )
    parser.add_argument(
        "--resolutions-file", type=Path, default=None,
        help="Path to gate resolutions JSON for readiness gating."
    )
    parser.add_argument(
        "--mark-publication-ready", action="store_true",
        help="Fail if any readiness gates remain unresolved."
    )
    return parser.parse_args()


def _write_metadata(
    output_dir: Path,
    year: int,
    state_summaries: dict[str, dict[str, int]],
    failures: list[str],
    args: argparse.Namespace,
) -> None:
    import os
    metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "command": "scripts/build_all_states_data_package.py",
        "acs_year": year,
        "api_key_set": bool(args.api_key or os.getenv("CENSUS_API_KEY")),
        "total_states_attempted": len(state_summaries),
        "failed_states": failures,
        "state_summaries": state_summaries,
        "total_counties": sum(s["counties"] for s in state_summaries.values()),
        "total_tracts": sum(s["tracts"] for s in state_summaries.values()),
        "total_population_points": sum(s["population_points"] for s in state_summaries.values()),
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
