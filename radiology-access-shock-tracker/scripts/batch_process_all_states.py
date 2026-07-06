from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from radshock.data.states import STATE_FIPS_MAP

GEOFABRIK_STATE_NAME: dict[str, str] = {
    "AL": "alabama", "AK": "alaska", "AZ": "arizona", "AR": "arkansas",
    "CA": "california", "CO": "colorado", "CT": "connecticut", "DE": "delaware",
    "FL": "florida", "GA": "georgia", "HI": "hawaii", "ID": "idaho",
    "IL": "illinois", "IN": "indiana", "IA": "iowa", "KS": "kansas",
    "KY": "kentucky", "LA": "louisiana", "ME": "maine", "MD": "maryland",
    "MA": "massachusetts", "MI": "michigan", "MN": "minnesota", "MS": "mississippi",
    "MO": "missouri", "MT": "montana", "NE": "nebraska", "NV": "nevada",
    "NH": "new-hampshire", "NJ": "new-jersey", "NM": "new-mexico",
    "NY": "new-york", "NC": "north-carolina", "ND": "north-dakota",
    "OH": "ohio", "OK": "oklahoma", "OR": "oregon", "PA": "pennsylvania",
    "RI": "rhode-island", "SC": "south-carolina", "SD": "south-dakota",
    "TN": "tennessee", "TX": "texas", "UT": "utah", "VT": "vermont",
    "VA": "virginia", "WA": "washington", "WV": "west-virginia",
    "WI": "wisconsin", "WY": "wyoming", "DC": "district-of-columbia",
    "PR": "puerto-rico",
}


def main() -> None:
    args = _parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_file = output_dir / "batch_checkpoint.json"
    checkpoint = _load_checkpoint(checkpoint_file) if args.resume else {}

    states = [s for s in STATE_FIPS_MAP if s not in args.skip]
    if args.states:
        states = [s for s in states if s in args.states]

    raw_completed = checkpoint.get("completed_states")
    raw_status = checkpoint.get("status_log")
    raw_review = checkpoint.get("review_items")
    completed: set[str] = set(raw_completed) if isinstance(raw_completed, list) else set()
    status_log: dict[str, str] = (
        dict(raw_status) if isinstance(raw_status, dict) else {}
    )
    review_items: list[dict[str, str]] = (
        raw_review if isinstance(raw_review, list) else []
    )

    for state_abbr in states:
        if state_abbr in completed:
            print(f"[SKIP] {state_abbr} already completed")
            continue

        print(f"\n{'='*60}")
        print(f"Processing {state_abbr}...")
        state_work = output_dir / state_abbr
        state_work.mkdir(parents=True, exist_ok=True)
        state_ok = True

        # Run non-human steps: fetch-fda-mqsa, prepare-mqsa-review, geocode-mqsa-review,
        # ingest-snapshot, prepare-travel-time, finalize-travel-time, resolve-gates
        single_cmd = [
            sys.executable, str(Path("scripts/process_single_state.py")),
            state_abbr,
            "--work-dir", str(state_work),
            "--step",
        ] + args.steps + [
            "--resolutions-file", str(args.resolutions_file),
        ] if args.resolutions_file else [
            sys.executable, str(Path("scripts/process_single_state.py")),
            state_abbr,
            "--work-dir", str(state_work),
            "--step",
        ] + args.steps

        print(f"Running: {' '.join(str(c) for c in single_cmd)}")
        result = subprocess.run(single_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"STDERR: {result.stderr}")
            status_log[state_abbr] = "FAILED"
            state_ok = False
        else:
            if result.stdout:
                print(result.stdout.strip()[-2000:])
            status_log[state_abbr] = "PASSED"

        # Generate review checklist
        checklist_path = output_dir / f"review_checklist_{state_abbr}.csv"
        try:
            rows = _build_review_checklist(state_abbr, state_work, result.stdout or "")
            with open(checklist_path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=[
                    "state", "gate", "status", "requires_human_review",
                    "output_path", "notes",
                ])
                w.writeheader()
                w.writerows(rows)
            review_items.extend(rows)
            print(f"Review checklist: {checklist_path}")
        except Exception as exc:
            print(f"WARNING: Could not write checklist: {exc}")

        if state_ok:
            completed.add(state_abbr)
            _save_checkpoint(checkpoint_file, completed, status_log, review_items)
        else:
            print(f"State {state_abbr} failed. Checkpoint saved for resume.")
            break

    # Write consolidated review manifest
    if review_items:
        manifest_path = output_dir / "review_manifest.csv"
        with open(manifest_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=review_items[0].keys())
            w.writeheader()
            w.writerows(review_items)
        print(f"\nConsolidated review manifest: {manifest_path}")

    summary_path = output_dir / "batch_summary.json"
    summary = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "total_states": len(states),
        "completed": len(completed),
        "failed": [s for s, st in status_log.items() if st == "FAILED"],
        "status_log": status_log,
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"\nBatch summary: {summary_path}")
    print(json.dumps(summary, indent=2))


def _build_review_checklist(
    state_abbr: str, state_work: Path, stdout: str,
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []

    mqsa_geo = state_work / f"mqsa_review_{state_abbr}_geocoded.csv"
    if mqsa_geo.exists():
        items.append({
            "state": state_abbr,
            "gate": "mqsa_review",
            "status": "needs_verification",
            "requires_human_review": "yes",
            "output_path": str(mqsa_geo),
            "notes": "Verify coordinates, set active=1, review_status=reviewed",
        })

    mqsa_final = state_work / f"facilities_{state_abbr}.csv"
    if mqsa_final.exists():
        items.append({
            "state": state_abbr,
            "gate": "mqsa_review",
            "status": "finalized",
            "requires_human_review": "no",
            "output_path": str(mqsa_final),
            "notes": "Ready for ingest",
        })

    hrsa_review = state_work / f"hrsa_review_{state_abbr}.csv"
    if hrsa_review.exists():
        items.append({
            "state": state_abbr,
            "gate": "hrsa_candidate_review",
            "status": "needs_verification",
            "requires_human_review": "yes",
            "output_path": str(hrsa_review),
            "notes": "Review candidate sites, mark approved/rejected",
        })

    tt_review = state_work / f"travel_time_review_{state_abbr}.csv"
    if tt_review.exists():
        items.append({
            "state": state_abbr,
            "gate": "travel_time_matrices",
            "status": "needs_verification",
            "requires_human_review": "yes",
            "output_path": str(tt_review),
            "notes": "Verify travel time entries",
        })

    tt_matrix = state_work / f"travel_time_matrix_{state_abbr}.csv"
    if tt_matrix.exists():
        items.append({
            "state": state_abbr,
            "gate": "travel_time_matrices",
            "status": "finalized",
            "requires_human_review": "no",
            "output_path": str(tt_matrix),
            "notes": "Matrix ready",
        })

    if "PASS" in stdout:
        items.append({
            "state": state_abbr,
            "gate": "all_automated",
            "status": "passed",
            "requires_human_review": "no",
            "output_path": "",
            "notes": "All automated steps completed",
        })

    return items


def _load_checkpoint(path: Path) -> dict[str, object]:
    if path.exists():
        data: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
        completed = data.get("completed_states", [])
        if isinstance(completed, list):
            print(f"Resumed from checkpoint: {path} ({len(completed)} states)")
        return data
    return {}


def _save_checkpoint(
    path: Path, completed: set[str], status_log: dict[str, str],
    review_items: list[dict[str, str]],
) -> None:
    data = {
        "completed_states": sorted(completed),
        "status_log": status_log,
        "review_items": review_items,
        "updated_at_utc": datetime.now(UTC).isoformat(),
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch-process all states (excluding NC) with checkpoint resume."
    )
    parser.add_argument("--output-dir", type=Path, default=Path("work/batch-processing"),
                        help="Output directory for per-state artifacts and checkpoints.")
    parser.add_argument("--skip", nargs="*", default=["NC", "PR"],
                        help="States to skip (default: NC PR).")
    parser.add_argument("--states", nargs="*", default=None,
                        help="Specific states to process (omit for all except --skip).")
    default_steps = [
        "fetch-fda-mqsa", "prepare-mqsa-review", "geocode-mqsa-review",
        "finalize-mqsa-review", "ingest-snapshot", "prepare-travel-time",
        "finalize-travel-time", "resolve-gates",
    ]
    parser.add_argument("--step", nargs="*", default=default_steps,
                        help="Steps to run per state (default: all non-HRSA steps).")
    parser.add_argument("--resolutions-file", type=Path, default=None,
                        help="Gate resolutions JSON file path.")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from checkpoint file in output-dir.")
    return parser.parse_args()


if __name__ == "__main__":
    main()
