import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from radshock.readiness import run_readiness_audit
from radshock.snapshots import file_sha256


def test_readiness_audit_blocks_synthetic_unverified_analysis(tmp_path: Path) -> None:
    analysis = tmp_path / "demo" / "analysis"
    analysis.mkdir(parents=True)
    (analysis.parent / "manifest.json").write_text('{"synthetic_data": true}\n')
    _events(analysis / "facility_events.csv", requires_verification=True)
    _county_shocks(analysis / "county_shocks.csv")
    _interventions(analysis / "intervention_rankings.csv")
    _sensitivity(analysis / "sensitivity_analysis.csv")
    audit = run_readiness_audit(analysis)
    check_statuses = {check.check_id: check.status for check in audit.checks}
    assert audit.overall_status == "BLOCKED"
    assert check_statuses["manifest"] == "BLOCKER"
    assert check_statuses["facility_events"] == "BLOCKER"


def test_readiness_audit_passes_verified_real_package(tmp_path: Path) -> None:
    package = tmp_path / "package"
    analysis = package / "analysis"
    briefs = package / "briefs"
    analysis.mkdir(parents=True)
    briefs.mkdir()
    (package / "manifest.json").write_text('{"synthetic_data": false}\n')
    _events(analysis / "facility_events.csv", requires_verification=False)
    _county_shocks(analysis / "county_shocks.csv")
    _interventions(analysis / "intervention_rankings.csv")
    _sensitivity(analysis / "sensitivity_analysis.csv")
    (briefs / "policy_brief.md").write_text("# Brief\n")
    before = _snapshot_dir(tmp_path / "snapshots" / "before")
    after = _snapshot_dir(tmp_path / "snapshots" / "after")
    source_metadata = tmp_path / "source.metadata.json"
    source_metadata.write_text(
        json.dumps(
            {
                "source_name": "reviewed-source",
                "retrieval_date": "2026-06-19",
                "retrieval_method": "local-archive",
                "sha256": "abc123",
            }
        )
        + "\n"
    )
    audit = run_readiness_audit(
        analysis,
        before_snapshot_dir=before,
        after_snapshot_dir=after,
        raw_source_metadata=source_metadata,
    )
    assert audit.overall_status == "WARN"
    warnings = {check.check_id for check in audit.checks if check.status == "WARN"}
    assert warnings == {"travel_time"}
    assert not any(check.status == "BLOCKER" for check in audit.checks)


def test_readiness_audit_accepts_manifest_inside_analysis_dir(tmp_path: Path) -> None:
    analysis = tmp_path / "analysis"
    analysis.mkdir()
    (analysis / "manifest.json").write_text('{"synthetic_data": false}\n')
    _events(analysis / "facility_events.csv", requires_verification=False)
    _county_shocks(analysis / "county_shocks.csv")
    _interventions(analysis / "intervention_rankings.csv")
    _sensitivity(analysis / "sensitivity_analysis.csv")
    (analysis / "policy_brief.md").write_text("# Brief\n")

    audit = run_readiness_audit(analysis)

    check_statuses = {check.check_id: check.status for check in audit.checks}
    assert check_statuses["manifest"] == "PASS"
    assert audit.overall_status == "WARN"


def test_readiness_audit_blocks_public_osrm_travel_time_provider(tmp_path: Path) -> None:
    analysis = tmp_path / "analysis"
    analysis.mkdir()
    (analysis / "manifest.json").write_text(
        json.dumps(
            {
                "synthetic_data": False,
                "routing": {
                    "provider": "osrm:driving",
                    "note": "public OSRM-compatible endpoint",
                },
            }
        )
        + "\n"
    )
    pd.DataFrame(columns=["event_type"]).to_csv(analysis / "facility_events.csv", index=False)
    _travel_time_county_shocks(analysis / "county_shocks.csv")
    _interventions(analysis / "intervention_rankings.csv")
    _sensitivity(analysis / "sensitivity_analysis.csv")
    (analysis / "policy_brief.md").write_text("# Brief\n")

    audit = run_readiness_audit(analysis, require_travel_time=True)

    check_statuses = {check.check_id: check.status for check in audit.checks}
    assert audit.overall_status == "BLOCKED"
    assert check_statuses["route_provider"] == "BLOCKER"


def test_readiness_audit_accepts_self_hosted_osrm_provenance(tmp_path: Path) -> None:
    analysis = tmp_path / "analysis"
    analysis.mkdir()
    (analysis / "manifest.json").write_text(
        json.dumps(
            {
                "synthetic_data": False,
                "routing": _self_hosted_routing_manifest(),
            }
        )
        + "\n"
    )
    pd.DataFrame(columns=["event_type"]).to_csv(analysis / "facility_events.csv", index=False)
    _travel_time_county_shocks(analysis / "county_shocks.csv")
    _interventions(analysis / "intervention_rankings.csv")
    _sensitivity(analysis / "sensitivity_analysis.csv")
    (analysis / "policy_brief.md").write_text("# Brief\n")

    audit = run_readiness_audit(analysis, require_travel_time=True)

    check_statuses = {check.check_id: check.status for check in audit.checks}
    assert check_statuses["route_provider"] == "PASS"


def test_readiness_audit_blocks_incomplete_private_route_provenance(tmp_path: Path) -> None:
    analysis = tmp_path / "analysis"
    analysis.mkdir()
    (analysis / "manifest.json").write_text(
        json.dumps(
            {
                "synthetic_data": False,
                "routing": {
                    "provider": "osrm:driving",
                    "route_source_url": "http://127.0.0.1:5000/table/v1/driving",
                    "matrix_metadata_json": "data/travel_times/matrix.metadata.json",
                },
            }
        )
        + "\n"
    )
    pd.DataFrame(columns=["event_type"]).to_csv(analysis / "facility_events.csv", index=False)
    _travel_time_county_shocks(analysis / "county_shocks.csv")
    _interventions(analysis / "intervention_rankings.csv")
    _sensitivity(analysis / "sensitivity_analysis.csv")
    (analysis / "policy_brief.md").write_text("# Brief\n")

    audit = run_readiness_audit(analysis, require_travel_time=True)

    route_provider = {check.check_id: check for check in audit.checks}["route_provider"]
    assert route_provider.status == "BLOCKER"
    assert "routing.map_extract" in route_provider.details


def test_readiness_audit_warns_on_county_centroid_placeholder_candidates(
    tmp_path: Path,
) -> None:
    analysis = tmp_path / "analysis"
    analysis.mkdir()
    (analysis / "manifest.json").write_text('{"synthetic_data": false}\n')
    pd.DataFrame(columns=["event_type"]).to_csv(analysis / "facility_events.csv", index=False)
    _county_shocks(analysis / "county_shocks.csv")
    pd.DataFrame(
        [
            {
                "candidate_id": "COUNTY-CENTROID-37001",
                "candidate_name": "Demo County Centroid",
                "intervention_score": 90.0,
            }
        ]
    ).to_csv(analysis / "intervention_rankings.csv", index=False)
    _sensitivity(analysis / "sensitivity_analysis.csv")
    (analysis / "policy_brief.md").write_text("# Brief\n")

    audit = run_readiness_audit(analysis)

    check_statuses = {check.check_id: check.status for check in audit.checks}
    assert check_statuses["interventions"] == "WARN"


def _events(path: Path, requires_verification: bool) -> None:
    pd.DataFrame(
        [
            {
                "facility_id": "F1",
                "facility_name": "Facility",
                "event_type": "POSSIBLE_CLOSURE",
                "severity": 1.0,
                "details": "ID absent from later snapshot; not a confirmed closure",
                "requires_verification": requires_verification,
            }
        ]
    ).to_csv(path, index=False)


def _county_shocks(path: Path) -> None:
    pd.DataFrame(
        [
            {
                "county_fips": "37001",
                "county_name": "Demo",
                "shock_score": 24.4,
                "alert_level": "WARNING",
                "shock_mean_distance_component": 0.5,
                "shock_p90_distance_component": 0.2,
                "shock_threshold_component": 0.1,
                "vulnerability_poverty_component": 0.2,
                "vulnerability_rurality_component": 0.4,
                "vulnerability_risk_component": 0.3,
            }
        ]
    ).to_csv(path, index=False)


def _travel_time_county_shocks(path: Path) -> None:
    pd.DataFrame(
        [
            {
                "county_fips": "37001",
                "county_name": "Demo",
                "shock_score": 0,
                "alert_level": "NONE",
                "access_metric": "travel_time_minutes",
                "mean_travel_time_minutes_before": 12.0,
                "mean_travel_time_minutes_after": 12.0,
                "travel_time_coverage_before": 1.0,
                "travel_time_coverage_after": 1.0,
            }
        ]
    ).to_csv(path, index=False)


def _self_hosted_routing_manifest() -> dict[str, object]:
    return {
        "provider": "osrm:driving",
        "profile": "driving",
        "route_source_url": "http://127.0.0.1:5000/table/v1/driving",
        "matrix_metadata_json": "data/travel_times/self_hosted_osrm_matrix.metadata.json",
        "traffic_assumption": "free-flow travel time; no live traffic",
        "engine": {
            "name": "Project OSRM",
            "version": "v6.0.0 container",
            "deployment": "self-hosted GitHub Actions runner",
        },
        "map_extract": {
            "name": "Geofabrik North Carolina",
            "source_url": "https://download.geofabrik.de/north-america/us/north-carolina-latest.osm.pbf",
            "osm_data_timestamp": "2026-06-17T20:21:14Z",
            "sha256": "abc123",
        },
    }


def _interventions(path: Path) -> None:
    pd.DataFrame(
        [{"candidate_id": "C1", "candidate_name": "Candidate", "intervention_score": 90.0}]
    ).to_csv(path, index=False)


def _sensitivity(path: Path) -> None:
    pd.DataFrame(
        [
            {"scenario_id": "baseline", "county_fips": "37001"},
            {"scenario_id": "threshold_heavy", "county_fips": "37001"},
        ]
    ).to_csv(path, index=False)


def _snapshot_dir(path: Path) -> Path:
    path.mkdir(parents=True)
    facilities = path / "facilities.csv"
    pd.DataFrame(
        [["F1", "Facility", 35.0, -78.0, 1000, True]],
        columns=[
            "facility_id",
            "facility_name",
            "latitude",
            "longitude",
            "annual_capacity",
            "active",
        ],
    ).to_csv(facilities, index=False)
    metadata = {
        "as_of": "2026-06-19",
        "source_name": "reviewed-source",
        "source_url": "https://example.test/source.csv",
        "raw_source_sha256": "abc123",
        "record_count": 1,
        "active_record_count": 1,
        "sha256": file_sha256(facilities),
        "created_at_utc": datetime.now(UTC).isoformat(),
    }
    (path / "metadata.json").write_text(json.dumps(metadata) + "\n")
    return path
