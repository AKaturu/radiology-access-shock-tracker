from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd

from radshock.access import compare_county_travel_time_access
from radshock.briefs import generate_policy_brief, generate_policy_brief_html
from radshock.changes import detect_changes
from radshock.intervention import simulate_candidates
from radshock.readiness import audit_to_json, render_readiness_markdown, run_readiness_audit
from radshock.sensitivity import run_sensitivity_analysis


def main() -> None:
    args = _parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    before = pd.read_csv(args.before_csv)
    after = pd.read_csv(args.after_csv)
    population = pd.read_csv(args.population_csv, dtype={"point_id": str, "county_fips": str})
    counties = pd.read_csv(args.counties_csv, dtype={"county_fips": str})
    candidates = pd.read_csv(args.candidates_csv, dtype={"candidate_id": str, "county_fips": str})
    before_times = pd.read_csv(args.before_travel_times_csv, dtype={"point_id": str})
    after_times = pd.read_csv(args.after_travel_times_csv, dtype={"point_id": str})

    events = detect_changes(before, after)
    shocks = compare_county_travel_time_access(
        population,
        before,
        after,
        counties,
        before_times,
        after_times,
        threshold_minutes=args.threshold_minutes,
    )
    interventions = simulate_candidates(population, after, candidates)
    sensitivity = run_sensitivity_analysis(shocks)

    events.to_csv(output_dir / "facility_events.csv", index=False)
    shocks.to_csv(output_dir / "county_shocks.csv", index=False)
    interventions.to_csv(output_dir / "intervention_rankings.csv", index=False)
    sensitivity.to_csv(output_dir / "sensitivity_analysis.csv", index=False)

    brief_date = _parse_optional_date(args.after_period)
    brief = generate_policy_brief(
        events,
        shocks,
        interventions,
        as_of=brief_date,
        synthetic_data=False,
    )
    (output_dir / "policy_brief.md").write_text(brief, encoding="utf-8")
    (output_dir / "policy_brief.html").write_text(
        generate_policy_brief_html(brief),
        encoding="utf-8",
    )

    manifest = _build_manifest(args)
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    audit = run_readiness_audit(
        output_dir,
        before_snapshot_dir=args.before_snapshot_dir,
        after_snapshot_dir=args.after_snapshot_dir,
        raw_source_metadata=args.raw_source_metadata,
        require_travel_time=True,
    )
    (output_dir / "readiness_audit.json").write_text(audit_to_json(audit), encoding="utf-8")
    (output_dir / "readiness_audit.md").write_text(
        render_readiness_markdown(audit),
        encoding="utf-8",
    )
    blocker_count = sum(check.status == "BLOCKER" for check in audit.checks)
    warning_count = sum(check.status == "WARN" for check in audit.checks)
    print(
        f"Travel-time package written: {output_dir.resolve()} "
        f"readiness={audit.overall_status} blockers={blocker_count} warnings={warning_count}"
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Finalize a route-time analysis package with production routing provenance."
    )
    parser.add_argument("--before-csv", type=Path, required=True)
    parser.add_argument("--after-csv", type=Path, required=True)
    parser.add_argument("--population-csv", type=Path, required=True)
    parser.add_argument("--counties-csv", type=Path, required=True)
    parser.add_argument("--candidates-csv", type=Path, required=True)
    parser.add_argument("--before-travel-times-csv", type=Path, required=True)
    parser.add_argument("--after-travel-times-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--before-snapshot-dir", type=Path, required=True)
    parser.add_argument("--after-snapshot-dir", type=Path, required=True)
    parser.add_argument("--raw-source-metadata", type=Path, required=True)
    parser.add_argument("--matrix-metadata-json", type=Path, required=True)
    parser.add_argument("--route-review-csv", type=Path, required=True)
    parser.add_argument("--candidate-review-metadata-json", type=Path)
    parser.add_argument("--before-period", default="2026-06-19")
    parser.add_argument("--after-period", default="2026-06-20")
    parser.add_argument("--threshold-minutes", type=float, default=45.0)
    parser.add_argument("--route-provider", default="osrm:driving")
    parser.add_argument("--route-profile", default="driving")
    parser.add_argument("--route-source-url", required=True)
    parser.add_argument("--engine-name", default="Project OSRM")
    parser.add_argument("--engine-version", required=True)
    parser.add_argument("--engine-deployment", required=True)
    parser.add_argument("--map-extract-name", default="Geofabrik North Carolina")
    parser.add_argument("--map-extract-url", required=True)
    parser.add_argument("--map-extract-osm-data-timestamp", required=True)
    parser.add_argument("--map-extract-sha256", required=True)
    parser.add_argument("--traffic-assumption", required=True)
    parser.add_argument("--routing-note", default="")
    return parser.parse_args()


def _build_manifest(args: argparse.Namespace) -> dict[str, object]:
    matrix_metadata = _read_json(args.matrix_metadata_json)
    candidate_metadata = (
        _read_json(args.candidate_review_metadata_json)
        if args.candidate_review_metadata_json is not None
        else None
    )
    manifest: dict[str, object] = {
        "synthetic_data": False,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "command": "scripts/finalize_travel_time_package.py",
        "access_metric": "travel_time_minutes",
        "inputs": {
            "before_csv": str(args.before_csv),
            "after_csv": str(args.after_csv),
            "population_csv": str(args.population_csv),
            "counties_csv": str(args.counties_csv),
            "candidates_csv": str(args.candidates_csv),
            "before_travel_times_csv": str(args.before_travel_times_csv),
            "after_travel_times_csv": str(args.after_travel_times_csv),
        },
        "periods": {
            "before_period": args.before_period,
            "after_period": args.after_period,
        },
        "outputs": {
            "events": "facility_events.csv",
            "county_shocks": "county_shocks.csv",
            "interventions": "intervention_rankings.csv",
            "sensitivity": "sensitivity_analysis.csv",
            "readiness_json": "readiness_audit.json",
            "readiness_md": "readiness_audit.md",
            "brief": "policy_brief.md",
            "brief_html": "policy_brief.html",
        },
        "routing": {
            "provider": args.route_provider,
            "profile": args.route_profile,
            "route_source_url": args.route_source_url,
            "matrix_csv": str(args.after_travel_times_csv),
            "matrix_metadata_json": str(args.matrix_metadata_json),
            "review_csv": str(args.route_review_csv),
            "traffic_assumption": args.traffic_assumption,
            "row_counts": matrix_metadata.get("row_counts", {}),
            "engine": {
                "name": args.engine_name,
                "version": args.engine_version,
                "deployment": args.engine_deployment,
            },
            "map_extract": {
                "name": args.map_extract_name,
                "source_url": args.map_extract_url,
                "osm_data_timestamp": args.map_extract_osm_data_timestamp,
                "sha256": args.map_extract_sha256,
            },
            "note": args.routing_note,
        },
    }
    if candidate_metadata is not None:
        manifest["candidate_assumptions"] = {
            "source": "HRSA Health Center Program Service Delivery and Look-Alike Sites",
            "candidate_review_csv": "data/candidate_sites_review.csv",
            "candidate_review_metadata_json": str(args.candidate_review_metadata_json),
            "candidate_sites_csv": str(args.candidates_csv),
            "row_counts": candidate_metadata.get("row_counts", {}),
            "source_urls": candidate_metadata.get("source_urls", []),
            "note": (
                "HRSA rows are active service-delivery health-center sites used as planning "
                "assumptions, not claims that candidate locations provide mammography."
            ),
        }
    return manifest


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_optional_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


if __name__ == "__main__":
    main()
