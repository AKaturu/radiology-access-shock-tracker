import pandas as pd

from radshock.access import compare_county_access, summarize_county_access


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
