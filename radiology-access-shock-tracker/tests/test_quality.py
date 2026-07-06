from __future__ import annotations

import pandas as pd

from radshock.quality import (
    build_data_quality_reports,
    build_geocoder_confidence,
    build_identifier_crosswalk,
    build_route_uncertainty_report,
)
from radshock.travel_times import TRAVEL_TIME_REVIEW_COLUMNS


def test_geocoder_confidence_and_identifier_crosswalk() -> None:
    review = _mqsa_review()

    confidence = build_geocoder_confidence(review)
    crosswalk = build_identifier_crosswalk(review)

    assert confidence.loc[0, "geocoder_confidence"] == "reviewed_high"
    assert crosswalk.loc[0, "facility_id"] == "MQSA-NC-1"
    assert crosswalk.loc[0, "source_record_hash"] == "hash1"


def test_route_uncertainty_report_flags_implausible_speed() -> None:
    report = build_route_uncertainty_report(_travel_review())
    metrics = {row.metric: row for row in report.itertuples(index=False)}

    assert metrics["route_rows"].value == 1
    assert metrics["high_implied_speed_flags"].status == "WARN"
    assert metrics["missing_provider_rows"].status == "PASS"


def test_build_data_quality_reports_writes_expected_tables() -> None:
    reports = build_data_quality_reports(
        facilities=_facilities(),
        population_points=_population(),
        mqsa_review=_mqsa_review(),
        travel_time_review=_travel_review(),
    )

    expected = {"data_quality", "geocoder_confidence", "identifier_crosswalk", "route_uncertainty"}
    assert expected <= set(reports)
    assert not reports["data_quality"].empty


def _facilities() -> pd.DataFrame:
    return pd.DataFrame(
        [["MQSA-NC-1", "Facility", 35.0, -78.0, "", True]],
        columns=[
            "facility_id",
            "facility_name",
            "latitude",
            "longitude",
            "annual_capacity",
            "active",
        ],
    )


def _population() -> pd.DataFrame:
    return pd.DataFrame(
        [["tract-1", "37001", 35.0, -78.0, 100]],
        columns=["point_id", "county_fips", "latitude", "longitude", "weight"],
    )


def _mqsa_review() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "facility_id": "MQSA-NC-1",
                "facility_name": "Facility",
                "source_record_hash": "hash1",
                "source_facility_name": "Facility Raw",
                "source_address_1": "100 Main St",
                "source_city": "Raleigh",
                "source_state": "NC",
                "source_zip_code": "27601",
                "source_name": "fda-mqsa-public",
                "source_schema_version": "pipe",
                "review_status": "reviewed",
                "latitude": "35.0",
                "longitude": "-78.0",
                "geocode_status": "matched",
                "geocode_provider": "census",
                "geocode_matched_address": "100 MAIN ST",
                "geocode_benchmark": "Public_AR_Current",
                "geocode_error": "",
                "coordinate_quality": "reviewed",
            }
        ]
    )


def _travel_review() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "point_id": "tract-1",
                "county_fips": "37001",
                "point_latitude": "35.0",
                "point_longitude": "-78.0",
                "point_weight": "100",
                "facility_id": "MQSA-NC-1",
                "facility_name": "Facility",
                "facility_latitude": "36.0",
                "facility_longitude": "-79.0",
                "active": "true",
                "straight_line_miles": "100",
                "travel_time_minutes": "30",
                "route_status": "routed",
                "route_provider": "self-hosted-osrm",
                "route_source_url": "http://127.0.0.1:5000/table/v1/driving",
                "route_retrieved_at_utc": "2026-06-20T00:00:00+00:00",
                "route_error": "",
                "review_status": "approved",
            }
        ],
        columns=TRAVEL_TIME_REVIEW_COLUMNS,
    )
