from __future__ import annotations

import pandas as pd

from radshock.geo import haversine_miles
from radshock.schemas import (
    TRAVEL_TIME_MATRIX_COLUMNS,
    validate_facilities,
    validate_population_points,
    validate_travel_time_matrix,
)

TRAVEL_TIME_REVIEW_APPROVED_STATUSES = {"reviewed", "verified", "approved"}
TRAVEL_TIME_ROUTE_STATUSES = {"routed", "unreachable", "excluded"}
TRAVEL_TIME_REVIEW_REQUIRED_COLUMNS = TRAVEL_TIME_MATRIX_COLUMNS | {
    "route_status",
    "review_status",
}

TRAVEL_TIME_REVIEW_COLUMNS = [
    "point_id",
    "county_fips",
    "point_latitude",
    "point_longitude",
    "point_weight",
    "facility_id",
    "facility_name",
    "facility_latitude",
    "facility_longitude",
    "active",
    "straight_line_miles",
    "travel_time_minutes",
    "route_status",
    "route_provider",
    "route_source_url",
    "route_retrieved_at_utc",
    "route_error",
    "review_status",
]


def build_travel_time_review_template(
    population_points: pd.DataFrame,
    facilities: pd.DataFrame,
    active_only: bool = True,
    max_distance_miles: float | None = None,
) -> pd.DataFrame:
    """Build a point-to-facility routing worklist without inventing travel times."""
    points = validate_population_points(population_points).rename(
        columns={
            "latitude": "point_latitude",
            "longitude": "point_longitude",
            "weight": "point_weight",
        }
    )
    facility_rows = validate_facilities(facilities).rename(
        columns={
            "latitude": "facility_latitude",
            "longitude": "facility_longitude",
        }
    )
    if active_only:
        facility_rows = facility_rows[facility_rows["active"]].reset_index(drop=True)

    if points.empty or facility_rows.empty:
        return pd.DataFrame(columns=TRAVEL_TIME_REVIEW_COLUMNS)

    pairs = points.assign(_route_key=1).merge(
        facility_rows.assign(_route_key=1),
        on="_route_key",
        how="inner",
    )
    pairs = pairs.drop(columns=["_route_key"])
    pairs["straight_line_miles"] = haversine_miles(
        pairs["point_latitude"].to_numpy(),
        pairs["point_longitude"].to_numpy(),
        pairs["facility_latitude"].to_numpy(),
        pairs["facility_longitude"].to_numpy(),
    ).round(3)
    if max_distance_miles is not None:
        if max_distance_miles <= 0:
            raise ValueError("max_distance_miles must be positive")
        pairs = pairs[pairs["straight_line_miles"] <= max_distance_miles].reset_index(drop=True)

    pairs["travel_time_minutes"] = ""
    pairs["route_status"] = "needs_route"
    pairs["route_provider"] = ""
    pairs["route_source_url"] = ""
    pairs["route_retrieved_at_utc"] = ""
    pairs["route_error"] = ""
    pairs["review_status"] = "needs_review"
    return pairs[TRAVEL_TIME_REVIEW_COLUMNS].sort_values(
        ["point_id", "straight_line_miles", "facility_id"]
    ).reset_index(drop=True)


def finalize_travel_time_review(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate reviewed routing rows and return a snapshot-ready travel-time matrix."""
    missing = sorted(TRAVEL_TIME_REVIEW_REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError("travel time review is missing required columns: " + ", ".join(missing))
    result = frame.copy()
    for column in ["point_id", "facility_id", "route_status", "review_status"]:
        result[column] = result[column].astype(str).str.strip()
    _require_unique_pairs(result)

    review_status = result["review_status"].str.lower()
    invalid_review = ~review_status.isin(TRAVEL_TIME_REVIEW_APPROVED_STATUSES)
    if invalid_review.any():
        examples = result.loc[invalid_review, ["point_id", "facility_id", "review_status"]].head(
            5
        )
        raise ValueError(
            "travel time review contains rows that are not approved: "
            + examples.to_dict(orient="records").__repr__()
        )

    route_status = result["route_status"].str.lower()
    invalid_route = ~route_status.isin(TRAVEL_TIME_ROUTE_STATUSES)
    if invalid_route.any():
        examples = result.loc[invalid_route, ["point_id", "facility_id", "route_status"]].head(5)
        raise ValueError(
            "travel time review contains invalid route_status values: "
            + examples.to_dict(orient="records").__repr__()
        )

    routed = result[route_status == "routed"].copy()
    if routed.empty:
        return pd.DataFrame(columns=sorted(TRAVEL_TIME_MATRIX_COLUMNS))
    routed["travel_time_minutes"] = pd.to_numeric(
        routed["travel_time_minutes"], errors="raise"
    )
    blank_minutes = routed["travel_time_minutes"].isna()
    if blank_minutes.any():
        examples = routed.loc[blank_minutes, ["point_id", "facility_id"]].head(5)
        raise ValueError(
            "routed travel time review rows are missing travel_time_minutes: "
            + examples.to_dict(orient="records").__repr__()
        )
    matrix = routed[["point_id", "facility_id", "travel_time_minutes"]]
    return validate_travel_time_matrix(matrix)


def _require_unique_pairs(frame: pd.DataFrame) -> None:
    duplicate_mask = frame.duplicated(["point_id", "facility_id"])
    if duplicate_mask.any():
        examples = frame.loc[duplicate_mask, ["point_id", "facility_id"]].head(5)
        raise ValueError(
            "travel time review contains duplicate point/facility pairs: "
            + examples.to_dict(orient="records").__repr__()
        )
