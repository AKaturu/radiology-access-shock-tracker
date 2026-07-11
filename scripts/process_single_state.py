from __future__ import annotations

# ruff: noqa: E402
"""Orchestrate data preparation for a single state.

Usage:
    python scripts/process_single_state.py <STATE> [--work-dir DIR] [--step STEP]
"""

import argparse
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from radshock.states import US_STATE_ABBR_TO_FIPS

STATE_FIPS_MAP = US_STATE_ABBR_TO_FIPS


def main() -> None:
    args = _parse_args()
    state = args.state.upper()
    if state not in STATE_FIPS_MAP:
        raise SystemExit(f"Unknown state abbreviation: {state}")
    work_dir = args.work_dir.resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    steps = _resolve_steps(args.step)
    if "resolve-gates" in steps and not args.resolve_reviewed_gates:
        raise SystemExit(
            "resolve-gates requires --resolve-reviewed-gates and reviewed evidence. "
            "Run the preparation steps first, complete human review, then resolve gates."
        )

    snapshot_date = date.today().isoformat()
    raw_dir = work_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    evidence_log: list[str] = []

    def _run(label: str, cmd: list[str], *, required: bool = True) -> None:
        print(f"\n=== {label} ===")
        print(f"Running: {' '.join(str(c) for c in cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print(f"STDERR: {result.stderr}")
            if required:
                raise SystemExit(f"Step failed: {label}")
            print(f"WARNING: Step failed but continuing: {label}")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        evidence_log.append(f"{label}: {'PASS' if result.returncode == 0 else 'FAIL'}")

    radshock = ["radshock"]

    # Step 1: Fetch FDA MQSA
    if "fetch-fda-mqsa" in steps:
        fda_archive_dir = work_dir / "fda-mqsa"
        _run(
            "Fetch FDA MQSA",
            radshock
            + [
                "fetch-fda-mqsa",
                "--output-dir",
                str(fda_archive_dir),
                "--force",
            ],
        )
        archive_path = list(fda_archive_dir.rglob("public.zip"))
        if archive_path:
            raw_dir.joinpath("fda-mqsa-archive.zip").write_bytes(archive_path[0].read_bytes())
        steps_completed.append("fetch-fda-mqsa")

    # Step 2: Prepare MQSA review
    mqsa_review_csv = work_dir / f"mqsa_review_{state}.csv"
    if "prepare-mqsa-review" in steps:
        mqsa_archive = raw_dir / "fda-mqsa-archive.zip"
        if not mqsa_archive.exists():
            print("WARNING: No MQSA archive found. Trying latest from work/fda-mqsa.")
            candidates = sorted(work_dir.rglob("public.zip"))
            if candidates:
                mqsa_archive = candidates[-1]
            else:
                print("No FDA MQSA archive available. Skipping MQSA steps.")
                skip = {
                    "prepare-mqsa-review",
                    "geocode-mqsa-review",
                    "finalize-mqsa-review",
                    "ingest-snapshot",
                }
                steps -= skip
                return
        _run(
            "Prepare MQSA review",
            radshock
            + [
                "prepare-mqsa-review",
                str(mqsa_archive),
                "--output-csv",
                str(mqsa_review_csv),
                "--state",
                state,
                "--force",
            ],
        )
        steps_completed.append("prepare-mqsa-review")

    # Step 3: Geocode MQSA review (automated fill via Census)
    mqsa_geocoded_csv = work_dir / f"mqsa_review_{state}_geocoded.csv"
    if "geocode-mqsa-review" in steps and mqsa_review_csv.exists():
        _run(
            "Geocode MQSA review",
            radshock
            + [
                "geocode-mqsa-review",
                str(mqsa_review_csv),
                "--output-csv",
                str(mqsa_geocoded_csv),
                "--provider",
                "census",
                "--overwrite-coordinates",
                "--force",
            ],
        )
        steps_completed.append("geocode-mqsa-review")
        print(f"\n!!! HUMAN REVIEW REQUIRED: Verify geocoding in {mqsa_geocoded_csv}")
        print("    Set active=1, review_status=reviewed, and fix coordinates before finalizing.")

    # Step 4: Finalize MQSA review
    mqsa_final_csv = work_dir / f"facilities_{state}.csv"
    if "finalize-mqsa-review" in steps:
        review_input = args.mqsa_review_csv or mqsa_geocoded_csv
        if not review_input.exists():
            print(f"WARNING: MQSA review input not found: {review_input}. Skipping.")
        else:
            _run(
                "Finalize MQSA review",
                radshock
                + [
                    "finalize-mqsa-review",
                    str(review_input),
                    "--output-csv",
                    str(mqsa_final_csv),
                    "--force",
                ],
            )
            steps_completed.append("finalize-mqsa-review")

    # Step 5: Ingest snapshot
    if "ingest-snapshot" in steps and mqsa_final_csv.exists():
        _run(
            "Ingest MQSA snapshot",
            radshock
            + [
                "ingest-snapshot",
                str(mqsa_final_csv),
                "--as-of",
                snapshot_date,
                "--source-name",
                "fda-mqsa-public",
                "--source-url",
                "https://www.accessdata.fda.gov/premarket/ftparea/public.zip",
            ],
        )
        steps_completed.append("ingest-snapshot")

    # Step 6: Prepare HRSA candidate review
    hrsa_review_csv = work_dir / f"hrsa_review_{state}.csv"
    if "prepare-hrsa-review" in steps:
        hrsa_input = args.hrsa_csv
        if hrsa_input and Path(hrsa_input).exists():
            _run(
                "Prepare HRSA candidate review",
                radshock
                + [
                    "prepare-hrsa-candidate-review",
                    str(hrsa_input),
                    "--output-csv",
                    str(hrsa_review_csv),
                    "--state",
                    state,
                    "--force",
                ],
            )
            steps_completed.append("prepare-hrsa-review")
        else:
            candidate_csv = work_dir / f"candidate_sites_{state}.csv"
            _run(
                "Prepare county-centroid candidate review (HRSA CSV not provided)",
                radshock
                + [
                    "prepare-candidate-review",
                    "--counties-csv",
                    str(work_dir / f"counties_{state}.csv"),
                    "--output-csv",
                    str(candidate_csv),
                    "--force",
                ],
            )
            print(f"!!! HUMAN REVIEW: Candidate review written to {candidate_csv}")

    # Step 7: Finalize HRSA candidate review
    hrsa_final_csv = work_dir / f"candidate_sites_{state}_final.csv"
    if "finalize-hrsa-review" in steps and hrsa_review_csv.exists():
        _run(
            "Finalize HRSA candidate review",
            radshock
            + [
                "finalize-candidate-review",
                str(hrsa_review_csv),
                "--output-csv",
                str(hrsa_final_csv),
                "--force",
            ],
        )
        steps_completed.append("finalize-hrsa-review")

    # Step 8: Prepare travel-time review
    travel_time_review_csv = work_dir / f"travel_time_review_{state}.csv"
    if "prepare-travel-time" in steps:
        pop_csv = args.population_csv or (work_dir / "population_points.csv")
        fac_csv = args.facilities_csv or mqsa_final_csv
        if pop_csv.exists() and fac_csv.exists():
            _run(
                "Prepare travel-time review",
                radshock
                + [
                    "prepare-travel-time-review",
                    "--population-csv",
                    str(pop_csv),
                    "--facilities-csv",
                    str(fac_csv),
                    "--output-csv",
                    str(travel_time_review_csv),
                    "--force",
                ],
            )
            steps_completed.append("prepare-travel-time")

    # Step 9: Finalize travel-time review
    travel_time_matrix_csv = work_dir / f"travel_time_matrix_{state}.csv"
    if "finalize-travel-time" in steps and travel_time_review_csv.exists():
        _run(
            "Finalize travel-time review",
            radshock
            + [
                "finalize-travel-time-review",
                str(travel_time_review_csv),
                "--output-csv",
                str(travel_time_matrix_csv),
                "--force",
            ],
        )
        steps_completed.append("finalize-travel-time")

    # Step 10: Resolve gates
    if "resolve-gates" in steps and args.resolutions_file:
        resolutions_file = Path(args.resolutions_file)
        for gate in ["mqsa_review", "hrsa_candidate_review", "travel_time_matrices"]:
            ts = datetime.now().isoformat()
            evidence = (
                f"Human-reviewed {state} evidence confirmed via process_single_state.py at {ts}"
            )
            _run(
                f"Resolve gate {gate} for {state}",
                radshock
                + [
                    "resolve-gate",
                    gate,
                    state,
                    "--evidence",
                    evidence,
                    "--resolutions-file",
                    str(resolutions_file),
                ],
                required=False,
            )
        steps_completed.append("resolve-gates")

    print(f"\n{'=' * 60}")
    print(f"State {state} processing complete.")
    print(f"Work directory: {work_dir}")
    print("Evidence log:")
    for entry in evidence_log:
        print(f"  {entry}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Process a single state through the data pipeline."
    )
    parser.add_argument("state", help="Two-letter state abbreviation (e.g. NC, VA, GA).")
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=Path("work/state-processing"),
        help="Working directory for state processing outputs.",
    )
    all_steps = ["fetch-fda-mqsa", "prepare-mqsa-review", "geocode-mqsa-review"]
    parser.add_argument(
        "--step",
        nargs="*",
        default=all_steps,
        help="Steps to run (default: FDA fetch, MQSA review prep, geocoding).",
    )
    parser.add_argument(
        "--mqsa-review-csv", type=Path, help="Pre-existing reviewed MQSA CSV (skip geocoding)."
    )
    parser.add_argument("--hrsa-csv", type=Path, help="HRSA Health Center Sites CSV input.")
    parser.add_argument(
        "--population-csv", type=Path, help="Population points CSV (for travel-time prep)."
    )
    parser.add_argument(
        "--facilities-csv", type=Path, help="Facilities CSV (for travel-time prep)."
    )
    parser.add_argument("--resolutions-file", type=Path, help="Gate resolutions JSON file.")
    parser.add_argument(
        "--resolve-reviewed-gates",
        action="store_true",
        help="Permit the resolve-gates step after human review has been completed.",
    )
    return parser.parse_args()


def _resolve_steps(step_names: list[str]) -> set[str]:
    return set(step_names)


steps_completed: list[str] = []


if __name__ == "__main__":
    main()
