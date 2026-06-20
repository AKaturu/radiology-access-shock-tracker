import json
from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from radshock.cli import app
from radshock.travel_times import TRAVEL_TIME_REVIEW_COLUMNS


def _snapshot(path: Path, rows: list[list[object]]) -> None:
    pd.DataFrame(
        rows,
        columns=[
            "facility_id",
            "facility_name",
            "latitude",
            "longitude",
            "annual_capacity",
            "active",
        ],
    ).to_csv(path, index=False)


def test_validate_snapshot_command(tmp_path: Path) -> None:
    snapshot = tmp_path / "snapshot.csv"
    _snapshot(snapshot, [["F1", "Facility", 35.0, -78.0, 1000, True]])
    result = CliRunner().invoke(app, ["validate-snapshot", str(snapshot)])
    assert result.exit_code == 0
    assert "Snapshot valid: 1 records, 1 active" in result.output


def test_compare_snapshots_command_writes_possible_closure(tmp_path: Path) -> None:
    before = tmp_path / "before.csv"
    after = tmp_path / "after.csv"
    output = tmp_path / "events.csv"
    _snapshot(before, [["F1", "Facility", 35.0, -78.0, 1000, True]])
    _snapshot(after, [])
    result = CliRunner().invoke(
        app,
        [
            "compare-snapshots",
            "--before-csv",
            str(before),
            "--after-csv",
            str(after),
            "--output-csv",
            str(output),
        ],
    )
    assert result.exit_code == 0
    events = pd.read_csv(output)
    assert events.loc[0, "event_type"] == "POSSIBLE_CLOSURE"


def test_prepare_mqsa_review_command(tmp_path: Path) -> None:
    source = tmp_path / "public.txt"
    source.write_text(
        f"{'Demo Facility':<75}"
        f"{'100 Main St':<50}"
        f"{'':<50}"
        f"{'':<50}"
        f"{'Raleigh':<50}"
        f"{'NC':<2}"
        f"{'27601':<15}"
        f"{'919-555-0100':<50}"
        f"{'':<50}"
        "\n"
    )
    output = tmp_path / "review.csv"
    result = CliRunner().invoke(
        app,
        ["prepare-mqsa-review", str(source), "--output-csv", str(output), "--state", "NC"],
    )
    assert result.exit_code == 0
    review = pd.read_csv(output, dtype=str).fillna("")
    assert review.loc[0, "source_facility_name"] == "Demo Facility"
    assert review.loc[0, "facility_id"] == ""
    assert review.loc[0, "active"] == ""


def test_finalize_mqsa_review_command_writes_snapshot_ready_csv(tmp_path: Path) -> None:
    review = tmp_path / "review.csv"
    output = tmp_path / "snapshot_ready.csv"
    pd.DataFrame(
        [
            {
                "facility_id": "MQSA-NC-0001",
                "facility_name": "Demo Facility",
                "latitude": "35.7796",
                "longitude": "-78.6382",
                "annual_capacity": "1000",
                "active": "true",
                "review_status": "reviewed",
                "source_record_hash": "abc123",
                "source_name": "fda-mqsa-public",
                "source_schema_version": "fda_mqsa_pipe_delimited",
            }
        ]
    ).to_csv(review, index=False)
    result = CliRunner().invoke(
        app,
        ["finalize-mqsa-review", str(review), "--output-csv", str(output)],
    )
    assert result.exit_code == 0
    snapshot_ready = pd.read_csv(output, dtype=str)
    assert snapshot_ready.loc[0, "facility_id"] == "MQSA-NC-0001"


def test_geocode_mqsa_review_command_uses_static_provider(tmp_path: Path) -> None:
    review = tmp_path / "review.csv"
    static = tmp_path / "static.csv"
    output = tmp_path / "geocoded.csv"
    pd.DataFrame(
        [
            {
                "facility_id": "",
                "facility_name": "Demo Facility",
                "latitude": "",
                "longitude": "",
                "annual_capacity": "",
                "active": "",
                "review_status": "needs_review",
                "source_record_hash": "abc123",
                "source_name": "fda-mqsa-public",
                "source_schema_version": "fda_mqsa_pipe_delimited",
                "source_facility_name": "Demo Facility",
                "source_address_1": "100 Main St",
                "source_city": "Raleigh",
                "source_state": "NC",
                "source_zip_code": "27601",
            }
        ]
    ).to_csv(review, index=False)
    pd.DataFrame(
        [
            {
                "source_record_hash": "abc123",
                "latitude": "35.7796",
                "longitude": "-78.6382",
                "matched_address": "100 MAIN ST, RALEIGH, NC, 27601",
            }
        ]
    ).to_csv(static, index=False)
    result = CliRunner().invoke(
        app,
        [
            "geocode-mqsa-review",
            str(review),
            "--output-csv",
            str(output),
            "--provider",
            "static",
            "--static-csv",
            str(static),
        ],
    )
    assert result.exit_code == 0
    geocoded = pd.read_csv(output, dtype=str)
    assert geocoded.loc[0, "latitude"] == "35.7796"
    assert geocoded.loc[0, "geocode_status"] == "matched"
    assert geocoded.loc[0, "review_status"] == "needs_review"


def test_compare_travel_time_access_command_writes_county_shocks(tmp_path: Path) -> None:
    before = tmp_path / "before.csv"
    after = tmp_path / "after.csv"
    population = tmp_path / "population.csv"
    counties = tmp_path / "counties.csv"
    before_times = tmp_path / "before_times.csv"
    after_times = tmp_path / "after_times.csv"
    output = tmp_path / "travel_time_shocks.csv"
    _snapshot(before, [["F1", "Facility", 35.0, -78.0, 1000, True]])
    _snapshot(after, [["F1", "Facility", 35.0, -78.0, 1000, True]])
    pd.DataFrame(
        [["P1", "37001", 35.0, -78.0, 100]],
        columns=["point_id", "county_fips", "latitude", "longitude", "weight"],
    ).to_csv(population, index=False)
    pd.DataFrame(
        [["37001", "Demo", "NC", 35.0, -78.0, 100, 20, 0.8, 0.7]],
        columns=[
            "county_fips",
            "county_name",
            "state",
            "centroid_lat",
            "centroid_lon",
            "eligible_population",
            "poverty_pct",
            "rurality_index",
            "high_risk_index",
        ],
    ).to_csv(counties, index=False)
    pd.DataFrame(
        [["P1", "F1", 20]],
        columns=["point_id", "facility_id", "travel_time_minutes"],
    ).to_csv(before_times, index=False)
    pd.DataFrame(
        [["P1", "F1", 55]],
        columns=["point_id", "facility_id", "travel_time_minutes"],
    ).to_csv(after_times, index=False)
    result = CliRunner().invoke(
        app,
        [
            "compare-travel-time-access",
            "--before-csv",
            str(before),
            "--after-csv",
            str(after),
            "--population-csv",
            str(population),
            "--counties-csv",
            str(counties),
            "--before-travel-times-csv",
            str(before_times),
            "--after-travel-times-csv",
            str(after_times),
            "--output-csv",
            str(output),
        ],
    )
    assert result.exit_code == 0
    shocks = pd.read_csv(output)
    assert shocks.loc[0, "access_metric"] == "travel_time_minutes"
    assert shocks.loc[0, "population_newly_over_45_minutes"] == 100


def test_prepare_and_finalize_travel_time_review_commands(tmp_path: Path) -> None:
    population = tmp_path / "population.csv"
    facilities = tmp_path / "facilities.csv"
    review = tmp_path / "travel_time_review.csv"
    matrix = tmp_path / "travel_time_matrix.csv"
    pd.DataFrame(
        [["P1", "37001", 35.0, -78.0, 100]],
        columns=["point_id", "county_fips", "latitude", "longitude", "weight"],
    ).to_csv(population, index=False)
    _snapshot(facilities, [["F1", "Facility", 35.0, -78.0, 1000, True]])
    prepared = CliRunner().invoke(
        app,
        [
            "prepare-travel-time-review",
            "--population-csv",
            str(population),
            "--facilities-csv",
            str(facilities),
            "--output-csv",
            str(review),
        ],
    )
    assert prepared.exit_code == 0
    route_review = pd.read_csv(review, dtype=str)
    route_review.loc[0, "travel_time_minutes"] = "18.5"
    route_review.loc[0, "route_status"] = "routed"
    route_review.loc[0, "route_provider"] = "fixture"
    route_review.loc[0, "review_status"] = "approved"
    route_review.to_csv(review, index=False)
    finalized = CliRunner().invoke(
        app,
        [
            "finalize-travel-time-review",
            str(review),
            "--output-csv",
            str(matrix),
        ],
    )
    assert finalized.exit_code == 0
    output = pd.read_csv(matrix)
    assert output.loc[0, "travel_time_minutes"] == 18.5


def test_fill_travel_time_review_openrouteservice_requires_env(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("OPENROUTESERVICE_API_KEY", raising=False)
    review = tmp_path / "travel_time_review.csv"
    output = tmp_path / "travel_time_review_ors.csv"
    pd.DataFrame(
        [
            {
                "point_id": "P1",
                "county_fips": "37001",
                "point_latitude": "35.0",
                "point_longitude": "-78.0",
                "point_weight": "100",
                "facility_id": "F1",
                "facility_name": "Facility",
                "facility_latitude": "35.0",
                "facility_longitude": "-78.0",
                "active": "true",
                "straight_line_miles": "0",
                "travel_time_minutes": "",
                "route_status": "needs_route",
                "route_provider": "",
                "route_source_url": "",
                "route_retrieved_at_utc": "",
                "route_error": "",
                "review_status": "needs_review",
            }
        ],
        columns=TRAVEL_TIME_REVIEW_COLUMNS,
    ).to_csv(review, index=False)

    result = CliRunner().invoke(
        app,
        [
            "fill-travel-time-review",
            str(review),
            "--output-csv",
            str(output),
            "--provider",
            "openrouteservice",
        ],
    )

    assert result.exit_code != 0
    assert "OPENROUTESERVICE_API_KEY is not set" in result.output


def test_sensitivity_analysis_command_writes_scenario_rows(tmp_path: Path) -> None:
    county_shocks = tmp_path / "county_shocks.csv"
    output = tmp_path / "sensitivity.csv"
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
    ).to_csv(county_shocks, index=False)
    result = CliRunner().invoke(
        app,
        [
            "sensitivity-analysis",
            str(county_shocks),
            "--output-csv",
            str(output),
        ],
    )
    assert result.exit_code == 0
    sensitivity = pd.read_csv(output)
    assert "baseline" in set(sensitivity["scenario_id"])
    assert "threshold_heavy" in set(sensitivity["scenario_id"])
    assert sensitivity.loc[0, "county_fips"] == 37001


def test_analyze_command_writes_manifest_and_readiness_reports(tmp_path: Path) -> None:
    before = tmp_path / "before.csv"
    after = tmp_path / "after.csv"
    population = tmp_path / "population.csv"
    counties = tmp_path / "counties.csv"
    candidates = tmp_path / "candidates.csv"
    output_dir = tmp_path / "analysis"
    _snapshot(before, [["F1", "Facility", 35.0, -78.0, 1000, True]])
    _snapshot(after, [["F1", "Facility", 35.0, -78.0, 1000, True]])
    pd.DataFrame(
        [["P1", "37001", 35.0, -78.0, 100]],
        columns=["point_id", "county_fips", "latitude", "longitude", "weight"],
    ).to_csv(population, index=False)
    pd.DataFrame(
        [["37001", "Demo", "NC", 35.0, -78.0, 100, 20, 0.8, 0.7]],
        columns=[
            "county_fips",
            "county_name",
            "state",
            "centroid_lat",
            "centroid_lon",
            "eligible_population",
            "poverty_pct",
            "rurality_index",
            "high_risk_index",
        ],
    ).to_csv(counties, index=False)
    pd.DataFrame(
        [["C1", "Candidate", "37001", 35.1, -78.1]],
        columns=["candidate_id", "candidate_name", "county_fips", "latitude", "longitude"],
    ).to_csv(candidates, index=False)

    result = CliRunner().invoke(
        app,
        [
            "analyze",
            "--before-csv",
            str(before),
            "--after-csv",
            str(after),
            "--population-csv",
            str(population),
            "--counties-csv",
            str(counties),
            "--candidates-csv",
            str(candidates),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert "Readiness status: WARN" in result.output
    manifest = json.loads((output_dir / "manifest.json").read_text())
    audit = json.loads((output_dir / "readiness_audit.json").read_text())
    assert manifest["synthetic_data"] is False
    assert manifest["outputs"]["readiness_json"] == "readiness_audit.json"
    assert audit["overall_status"] == "WARN"
    assert (output_dir / "readiness_audit.md").exists()


def test_readiness_audit_command_writes_reports(tmp_path: Path) -> None:
    analysis = tmp_path / "analysis"
    analysis.mkdir()
    (tmp_path / "manifest.json").write_text('{"synthetic_data": true}\n')
    pd.DataFrame(
        [
            {
                "event_type": "POSSIBLE_CLOSURE",
                "requires_verification": True,
            }
        ]
    ).to_csv(analysis / "facility_events.csv", index=False)
    pd.DataFrame(
        [
            {
                "county_fips": "37001",
                "county_name": "Demo",
                "shock_score": 24.4,
                "alert_level": "WARNING",
            }
        ]
    ).to_csv(analysis / "county_shocks.csv", index=False)
    pd.DataFrame([{"candidate_id": "C1"}]).to_csv(
        analysis / "intervention_rankings.csv",
        index=False,
    )
    json_output = tmp_path / "readiness.json"
    md_output = tmp_path / "readiness.md"
    result = CliRunner().invoke(
        app,
        [
            "readiness-audit",
            "--analysis-dir",
            str(analysis),
            "--output-json",
            str(json_output),
            "--output-md",
            str(md_output),
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(json_output.read_text())
    assert payload["overall_status"] == "BLOCKED"
    assert "Production Readiness Audit" in md_output.read_text()
