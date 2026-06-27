import json
from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from radshock.cli import _merge_filled_route_rows, app
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


def test_data_quality_report_command_passes_valid_facilities(tmp_path: Path) -> None:
    snapshot = tmp_path / "snapshot.csv"
    output_json = tmp_path / "quality.json"
    output_md = tmp_path / "quality.md"
    _snapshot(snapshot, [["F1", "Facility", 35.0, -78.0, 1000, True]])

    result = CliRunner().invoke(
        app,
        [
            "data-quality-report",
            str(snapshot),
            "--dataset-type",
            "facilities",
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(output_json.read_text())
    assert payload["status"] == "PASS"
    assert payload["dataset_type"] == "facilities"
    assert payload["row_count"] == 1
    assert "Data Quality Report" in output_md.read_text()


def test_data_quality_report_command_fails_duplicate_and_blank_values(tmp_path: Path) -> None:
    snapshot = tmp_path / "snapshot.csv"
    output_json = tmp_path / "quality.json"
    _snapshot(
        snapshot,
        [
            ["F1", "Facility", "", -78.0, 1000, True],
            ["F1", "Facility Duplicate", 91.0, -181.0, 1000, True],
        ],
    )

    result = CliRunner().invoke(
        app,
        [
            "data-quality-report",
            str(snapshot),
            "--output-json",
            str(output_json),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(output_json.read_text())
    checks = {check["id"]: check for check in payload["checks"]}
    assert payload["status"] == "FAIL"
    assert checks["blank_required_values"]["status"] == "FAIL"
    assert checks["duplicate_keys"]["status"] == "FAIL"
    assert checks["coordinate_ranges"]["status"] == "FAIL"


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


def test_archive_source_command_accepts_retrieved_on(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("raw data\n")
    output_dir = tmp_path / "raw"
    result = CliRunner().invoke(
        app,
        [
            "archive-source",
            str(source),
            "--source-name",
            "test-source",
            "--output-dir",
            str(output_dir),
            "--retrieved-on",
            "2026-06-20",
        ],
    )

    assert result.exit_code == 0
    metadata = json.loads(
        (output_dir / "test-source" / "2026-06-20" / "source.txt.metadata.json").read_text()
    )
    assert metadata["retrieval_date"] == "2026-06-20"


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


def test_carry_forward_mqsa_review_command_writes_metadata(tmp_path: Path) -> None:
    current = tmp_path / "current.csv"
    previous = tmp_path / "previous.csv"
    output = tmp_path / "carried.csv"
    metadata = tmp_path / "carried.metadata.json"
    current_rows = pd.DataFrame(
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
            },
            {
                "facility_id": "",
                "facility_name": "New Facility",
                "latitude": "",
                "longitude": "",
                "annual_capacity": "",
                "active": "",
                "review_status": "needs_review",
                "source_record_hash": "new123",
                "source_name": "fda-mqsa-public",
                "source_schema_version": "fda_mqsa_pipe_delimited",
            },
        ]
    )
    previous_rows = current_rows.iloc[[0]].copy()
    previous_rows.loc[0, "facility_id"] = "MQSA-NC-0001"
    previous_rows.loc[0, "latitude"] = "35.7796"
    previous_rows.loc[0, "longitude"] = "-78.6382"
    previous_rows.loc[0, "active"] = "true"
    previous_rows.loc[0, "review_status"] = "reviewed"
    current_rows.to_csv(current, index=False)
    previous_rows.to_csv(previous, index=False)

    result = CliRunner().invoke(
        app,
        [
            "carry-forward-mqsa-review",
            str(current),
            "--previous-review-csv",
            str(previous),
            "--output-csv",
            str(output),
            "--metadata-json",
            str(metadata),
        ],
    )

    assert result.exit_code == 0
    carried = pd.read_csv(output, dtype=str).fillna("")
    payload = json.loads(metadata.read_text())
    assert carried.loc[0, "facility_id"] == "MQSA-NC-0001"
    assert carried.loc[1, "review_status"] == "needs_review"
    assert payload["row_counts"]["matched_previous_source_hashes"] == 1
    assert payload["row_counts"]["needs_review_rows"] == 1


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


def test_fetch_census_population_points_command_writes_metadata(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output = tmp_path / "population_points_tracts.csv"
    raw_context = tmp_path / "census_tract_context.csv"
    metadata = tmp_path / "metadata.json"
    monkeypatch.setenv("CENSUS_API_KEY", "test-key")
    monkeypatch.setattr(
        "radshock.cli.build_nc_tract_analysis_context",
        lambda **kwargs: pd.DataFrame(
            [
                {
                    "tract_geoid": "37001020100",
                    "county_fips": "37001",
                    "centroid_lat": 35.1,
                    "centroid_lon": -78.1,
                    "eligible_population": 46,
                },
                {
                    "tract_geoid": "37001020200",
                    "county_fips": "37001",
                    "centroid_lat": 35.2,
                    "centroid_lon": -78.2,
                    "eligible_population": 0,
                },
            ]
        ),
    )

    result = CliRunner().invoke(
        app,
        [
            "fetch-census-population-points",
            "--output-csv",
            str(output),
            "--raw-context-csv",
            str(raw_context),
            "--metadata-json",
            str(metadata),
        ],
    )

    assert result.exit_code == 0
    points = pd.read_csv(output, dtype={"point_id": str, "county_fips": str})
    payload = json.loads(metadata.read_text())
    assert len(points) == 1
    assert points.loc[0, "point_id"] == "tract-37001020100"
    assert payload["geography"] == "tract"
    assert payload["row_counts"]["tracts"] == 2
    assert payload["row_counts"]["population_points"] == 1
    assert payload["outputs"]["population_points"]["sha256"]


def test_prepare_and_finalize_candidate_review_commands(tmp_path: Path) -> None:
    counties = tmp_path / "counties.csv"
    review = tmp_path / "candidate_review.csv"
    metadata = tmp_path / "candidate_review.metadata.json"
    output = tmp_path / "candidate_sites.csv"
    pd.DataFrame(
        [["37001", "Alamance", "NC", 36.04, -79.39, 1000, 10.0, 0.2, 0.3]],
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

    prepared = CliRunner().invoke(
        app,
        [
            "prepare-candidate-review",
            "--counties-csv",
            str(counties),
            "--output-csv",
            str(review),
            "--metadata-json",
            str(metadata),
        ],
    )

    assert prepared.exit_code == 0
    review_frame = pd.read_csv(review, dtype=str)
    payload = json.loads(metadata.read_text())
    assert review_frame.loc[0, "review_status"] == "needs_review"
    assert payload["row_counts"]["candidate_rows"] == 1

    blocked = CliRunner().invoke(
        app,
        ["finalize-candidate-review", str(review), "--output-csv", str(output)],
    )
    assert blocked.exit_code != 0
    assert blocked.exception is not None
    assert "not approved" in str(blocked.exception)

    review_frame.loc[0, "review_status"] = "reviewed"
    review_frame.to_csv(review, index=False)
    finalized = CliRunner().invoke(
        app,
        [
            "finalize-candidate-review",
            str(review),
            "--output-csv",
            str(output),
            "--metadata-json",
            str(tmp_path / "candidate_sites.metadata.json"),
        ],
    )

    assert finalized.exit_code == 0
    candidates = pd.read_csv(output, dtype={"candidate_id": str, "county_fips": str})
    finalized_payload = json.loads((tmp_path / "candidate_sites.metadata.json").read_text())
    assert candidates.loc[0, "candidate_id"] == "COUNTY-CENTROID-37001"
    assert finalized_payload["row_counts"]["candidate_rows"] == 1
    assert finalized_payload["output"]["sha256"]


def test_prepare_hrsa_candidate_review_command_writes_metadata(tmp_path: Path) -> None:
    source = tmp_path / "hrsa_sites.csv"
    review = tmp_path / "hrsa_candidate_review.csv"
    metadata = tmp_path / "hrsa_candidate_review.metadata.json"
    pd.DataFrame(
        [
            {
                "BPHC Assigned Number": "BPS-H80-000001",
                "Site Name": "Demo Health Center",
                "Site Address": "100 Main St",
                "Site City": "Raleigh",
                "Site State Abbreviation": "NC",
                "Site Postal Code": "27601",
                "Health Center Location Type Description": "Permanent",
                "Health Center Type Description": "Service Delivery Site",
                "Site Status Description": "Active",
                "Geocoding Artifact Address Primary X Coordinate": "-78.6382",
                "Geocoding Artifact Address Primary Y Coordinate": "35.7796",
                "State and County Federal Information Processing Standard Code": "37001",
            },
            {
                "BPHC Assigned Number": "BPS-H80-000002",
                "Site Name": "Demo Mobile Unit",
                "Site Address": "200 Main St",
                "Site City": "Raleigh",
                "Site State Abbreviation": "NC",
                "Site Postal Code": "27601",
                "Health Center Location Type Description": "Mobile Van",
                "Health Center Type Description": "Service Delivery Site",
                "Site Status Description": "Active",
                "Geocoding Artifact Address Primary X Coordinate": "-78.7",
                "Geocoding Artifact Address Primary Y Coordinate": "35.8",
                "State and County Federal Information Processing Standard Code": "37003",
            },
        ]
    ).to_csv(source, index=False)

    result = CliRunner().invoke(
        app,
        [
            "prepare-hrsa-candidate-review",
            str(source),
            "--output-csv",
            str(review),
            "--metadata-json",
            str(metadata),
            "--review-status",
            "reviewed",
        ],
    )

    assert result.exit_code == 0
    review_frame = pd.read_csv(review, dtype=str)
    payload = json.loads(metadata.read_text())
    assert len(review_frame) == 2
    assert set(review_frame["candidate_type"]) == {
        "fixed_site_assumption",
        "mobile_stop_assumption",
    }
    assert set(review_frame["review_status"]) == {"reviewed"}
    assert payload["row_counts"]["candidate_rows"] == 2
    assert payload["row_counts"]["candidate_types"]["mobile_stop_assumption"] == 1
    assert payload["filters"]["active_only"] is True
    assert payload["filters"]["service_delivery_only"] is True
    assert "data.hrsa.gov/data/download" in payload["source_urls"][0]


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
    metadata = tmp_path / "travel_time_review.metadata.json"
    matrix = tmp_path / "travel_time_matrix.csv"
    matrix_metadata = tmp_path / "travel_time_matrix.metadata.json"
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
            "--metadata-json",
            str(metadata),
            "--max-facilities-per-point",
            "1",
        ],
    )
    assert prepared.exit_code == 0
    payload = json.loads(metadata.read_text())
    assert payload["row_counts"]["route_pairs"] == 1
    assert payload["filters"]["max_facilities_per_point"] == 1
    assert payload["output"]["sha256"]
    route_review = pd.read_csv(review, dtype=str)
    route_review.loc[0, "travel_time_minutes"] = "18.5"
    route_review.loc[0, "route_status"] = "routed"
    route_review.loc[0, "route_provider"] = "fixture"
    route_review.loc[0, "route_source_url"] = "https://example.test/routes"
    route_review.loc[0, "route_retrieved_at_utc"] = "2026-06-20T00:00:00+00:00"
    route_review.loc[0, "review_status"] = "approved"
    route_review.to_csv(review, index=False)
    finalized = CliRunner().invoke(
        app,
        [
            "finalize-travel-time-review",
            str(review),
            "--output-csv",
            str(matrix),
            "--metadata-json",
            str(matrix_metadata),
        ],
    )
    assert finalized.exit_code == 0
    output = pd.read_csv(matrix)
    matrix_payload = json.loads(matrix_metadata.read_text())
    assert output.loc[0, "travel_time_minutes"] == 18.5
    assert matrix_payload["route_metadata"]["route_providers"] == ["fixture"]
    assert matrix_payload["route_metadata"]["route_source_urls"] == ["https://example.test/routes"]


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


def test_fill_travel_time_review_can_limit_missing_origins(
    tmp_path: Path,
    monkeypatch,
) -> None:
    review = tmp_path / "travel_time_review.csv"
    output = tmp_path / "travel_time_review_filled.csv"
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
            },
            {
                "point_id": "P2",
                "county_fips": "37001",
                "point_latitude": "36.0",
                "point_longitude": "-79.0",
                "point_weight": "50",
                "facility_id": "F1",
                "facility_name": "Facility",
                "facility_latitude": "35.0",
                "facility_longitude": "-78.0",
                "active": "true",
                "straight_line_miles": "90",
                "travel_time_minutes": "",
                "route_status": "needs_route",
                "route_provider": "",
                "route_source_url": "",
                "route_retrieved_at_utc": "",
                "route_error": "",
                "review_status": "needs_review",
            },
        ],
        columns=TRAVEL_TIME_REVIEW_COLUMNS,
    ).to_csv(review, index=False)

    def fake_fill(frame: pd.DataFrame, **kwargs: object) -> pd.DataFrame:
        assert set(frame["point_id"]) == {"P1"}
        result = frame.copy()
        result["travel_time_minutes"] = "12.5"
        result["route_status"] = "routed"
        result["route_provider"] = "fixture"
        result["route_source_url"] = "https://example.test/routes"
        result["route_retrieved_at_utc"] = "2026-06-20T00:00:00+00:00"
        result["route_error"] = ""
        return result

    monkeypatch.setattr("radshock.cli.fill_travel_time_review_from_osrm", fake_fill)

    result = CliRunner().invoke(
        app,
        [
            "fill-travel-time-review",
            str(review),
            "--output-csv",
            str(output),
            "--provider",
            "osrm",
            "--only-missing",
            "--max-origins",
            "1",
        ],
    )

    assert result.exit_code == 0
    filled = pd.read_csv(output, dtype=str).fillna("")
    assert filled.loc[0, "route_status"] == "routed"
    assert filled.loc[1, "route_status"] == "needs_route"


def test_merge_filled_route_rows_updates_only_subset_with_numeric_minutes() -> None:
    input_frame = pd.DataFrame(
        [
            {"point_id": "P1", "travel_time_minutes": "", "route_status": "needs_route"},
            {"point_id": "P2", "travel_time_minutes": "12.0", "route_status": "routed"},
        ],
        dtype="string",
    )
    filled = pd.DataFrame(
        [{"point_id": "P1", "travel_time_minutes": 10.5, "route_status": "routed"}],
        index=[0],
    )

    result = _merge_filled_route_rows(input_frame, filled)

    assert result.loc[0, "travel_time_minutes"] == 10.5
    assert result.loc[0, "route_status"] == "routed"
    assert result.loc[1, "travel_time_minutes"] == "12.0"


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
