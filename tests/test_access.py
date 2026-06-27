import pandas as pd

from radshock.access import (
    compare_county_access,
    compare_county_travel_time_access,
    nearest_travel_time_access,
    summarize_county_access,
)
from radshock.schemas import validate_travel_time_matrix


def _facilities(longitude: float) -> pd.DataFrame:
    return pd.DataFrame(
        [["F1", "Facility", 35.0, longitude, 1000, True]],
        columns=[
            "facility_id",
            "facility_name",
            "latitude",
            "longitude",
            "annual_capacity",
            "active",
        ],
    )


def test_county_distance_increases_after_facility_moves() -> None:
    points = pd.DataFrame(
        [["P1", "37001", 35.0, -78.0, 100]],
        columns=["point_id", "county_fips", "latitude", "longitude", "weight"],
    )
    counties = pd.DataFrame(
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
    )
    result = compare_county_access(points, _facilities(-78.0), _facilities(-79.0), counties)
    assert result.loc[0, "mean_distance_delta"] > 50
    assert result.loc[0, "shock_score"] > 0
    assert result.loc[0, "deterioration_component"] > 0
    assert result.loc[0, "vulnerability_component"] > 0
    assert "population_newly_over_30_miles" in result.columns


def test_weighted_mean_uses_population_weights() -> None:
    points = pd.DataFrame(
        [
            ["P1", "37001", 35.0, -78.0, 90],
            ["P2", "37001", 35.0, -79.0, 10],
        ],
        columns=["point_id", "county_fips", "latitude", "longitude", "weight"],
    )
    result = summarize_county_access(points, _facilities(-78.0))
    assert 5 < result.loc[0, "mean_distance_miles"] < 10


def test_no_active_facilities_marks_population_over_threshold() -> None:
    points = pd.DataFrame(
        [["P1", "37001", 35.0, -78.0, 100]],
        columns=["point_id", "county_fips", "latitude", "longitude", "weight"],
    )
    facilities = pd.DataFrame(
        [["F1", "Facility", 35.0, -78.0, 1000, False]],
        columns=[
            "facility_id",
            "facility_name",
            "latitude",
            "longitude",
            "annual_capacity",
            "active",
        ],
    )
    result = summarize_county_access(points, facilities)
    assert result.loc[0, "pct_over_30_miles"] == 1.0


def test_nearest_travel_time_access_uses_fastest_active_facility() -> None:
    points = pd.DataFrame(
        [["P1", "37001", 35.0, -78.0, 100]],
        columns=["point_id", "county_fips", "latitude", "longitude", "weight"],
    )
    facilities = pd.DataFrame(
        [
            ["F1", "Far Drive", 35.0, -78.0, 1000, True],
            ["F2", "Fast Drive", 35.0, -79.0, 1000, True],
            ["F3", "Inactive", 35.0, -77.0, 1000, False],
        ],
        columns=[
            "facility_id",
            "facility_name",
            "latitude",
            "longitude",
            "annual_capacity",
            "active",
        ],
    )
    travel_times = pd.DataFrame(
        [
            ["P1", "F1", 50],
            ["P1", "F2", 20],
            ["P1", "F3", 5],
        ],
        columns=["point_id", "facility_id", "travel_time_minutes"],
    )
    result = nearest_travel_time_access(points, facilities, travel_times)
    assert result.loc[0, "nearest_facility_id"] == "F2"
    assert result.loc[0, "travel_time_minutes"] == 20


def test_compare_county_travel_time_access_flags_new_threshold_population() -> None:
    points = pd.DataFrame(
        [["P1", "37001", 35.0, -78.0, 100]],
        columns=["point_id", "county_fips", "latitude", "longitude", "weight"],
    )
    counties = pd.DataFrame(
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
    )
    before_times = pd.DataFrame(
        [["P1", "F1", 20]],
        columns=["point_id", "facility_id", "travel_time_minutes"],
    )
    after_times = pd.DataFrame(
        [["P1", "F1", 55]],
        columns=["point_id", "facility_id", "travel_time_minutes"],
    )
    result = compare_county_travel_time_access(
        points,
        _facilities(-78.0),
        _facilities(-78.0),
        counties,
        before_times,
        after_times,
    )
    assert result.loc[0, "access_metric"] == "travel_time_minutes"
    assert result.loc[0, "mean_travel_time_delta"] == 35
    assert result.loc[0, "population_newly_over_45_minutes"] == 100
    assert result.loc[0, "shock_score"] > 0


def test_duplicate_travel_time_matrix_rows_are_rejected() -> None:
    travel_times = pd.DataFrame(
        [
            ["P1", "F1", 20],
            ["P1", "F1", 22],
        ],
        columns=["point_id", "facility_id", "travel_time_minutes"],
    )
    try:
        validate_travel_time_matrix(travel_times)
    except ValueError as exc:
        assert "duplicate point/facility pairs" in str(exc)
    else:
        raise AssertionError("duplicate travel-time rows should be rejected")
