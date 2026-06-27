from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import pandas as pd
import requests

from radshock.geo import haversine_miles
from radshock.schemas import (
    TRAVEL_TIME_MATRIX_COLUMNS,
    require_columns,
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

DEFAULT_OSRM_BASE_URL = "https://router.project-osrm.org"
DEFAULT_ORS_BASE_URL = "https://api.openrouteservice.org"
DEFAULT_ORS_PROFILE = "driving-car"
DEFAULT_ROUTE_USER_AGENT = "radshock-route-review/0.1"


def build_travel_time_review_template(
    population_points: pd.DataFrame,
    facilities: pd.DataFrame,
    active_only: bool = True,
    max_distance_miles: float | None = None,
    max_facilities_per_point: int | None = None,
) -> pd.DataFrame:
    """Build a point-to-facility routing worklist without inventing travel times."""
    if max_facilities_per_point is not None and max_facilities_per_point <= 0:
        raise ValueError("max_facilities_per_point must be positive")
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
    if max_facilities_per_point is not None and not pairs.empty:
        pairs = (
            pairs.sort_values(["point_id", "straight_line_miles", "facility_id"])
            .groupby("point_id", sort=False)
            .head(max_facilities_per_point)
            .reset_index(drop=True)
        )

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


def limit_travel_time_review_origins(
    frame: pd.DataFrame,
    max_origins: int | None,
) -> pd.DataFrame:
    """Return only the first N point_id groups while preserving original row indexes."""
    if max_origins is None:
        return frame.copy()
    if max_origins <= 0:
        raise ValueError("max_origins must be positive")
    require_columns(frame, {"point_id"}, "travel time review")
    point_ids = frame["point_id"].astype(str).drop_duplicates().head(max_origins)
    return frame.loc[frame["point_id"].astype(str).isin(set(point_ids))].copy()


def fill_travel_time_review_from_osrm(
    frame: pd.DataFrame,
    *,
    base_url: str = DEFAULT_OSRM_BASE_URL,
    profile: str = "driving",
    timeout: int = 60,
    user_agent: str = DEFAULT_ROUTE_USER_AGENT,
    review_status: str = "needs_review",
    request_delay_seconds: float = 0,
    session: Any | None = None,
) -> pd.DataFrame:
    """Fill a route-review worklist from an OSRM-compatible table endpoint.

    The function populates candidate route minutes and provider metadata. It does not make the
    result publication-ready by itself; callers should leave ``review_status`` as ``needs_review``
    until the route provider, network vintage, traffic assumptions, and output rows are reviewed.
    """
    require_columns(frame, set(TRAVEL_TIME_REVIEW_COLUMNS), "travel time review")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if request_delay_seconds < 0:
        raise ValueError("request_delay_seconds must be nonnegative")
    cleaned_profile = profile.strip("/")
    if not cleaned_profile:
        raise ValueError("profile must not be blank")

    result = frame.copy()
    for column in [
        "travel_time_minutes",
        "route_status",
        "route_provider",
        "route_source_url",
        "route_retrieved_at_utc",
        "route_error",
        "review_status",
    ]:
        result[column] = result[column].astype("object")
    for column in ["point_id", "facility_id", "route_status", "review_status"]:
        result[column] = result[column].astype(str).str.strip()
    _require_unique_pairs(result)
    _reset_route_output_columns(result)

    provider = f"osrm:{cleaned_profile}"
    endpoint_base = base_url.rstrip("/")
    source_url = f"{endpoint_base}/table/v1/{quote(cleaned_profile)}"
    http = session or requests.Session()
    headers = {"User-Agent": user_agent} if user_agent else {}
    retrieved_at = datetime.now(UTC).isoformat()

    for _, group in result.groupby("point_id", sort=False):
        index = group.index
        origin = group.iloc[0]
        coordinates = [
            _format_osrm_coordinate(origin["point_longitude"], origin["point_latitude"])
        ]
        coordinates.extend(
            _format_osrm_coordinate(row.facility_longitude, row.facility_latitude)
            for row in group.itertuples(index=False)
        )
        destinations = ";".join(str(i) for i in range(1, len(coordinates)))
        url = (
            f"{source_url}/{';'.join(coordinates)}"
            f"?sources=0&destinations={destinations}&annotations=duration&skip_waypoints=true"
        )
        try:
            response = http.get(url, timeout=timeout, headers=headers)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # pragma: no cover - exact requests exceptions vary by version
            result.loc[index, "route_error"] = f"OSRM request failed: {exc}"
            continue

        if payload.get("code") != "Ok":
            result.loc[index, "route_error"] = f"OSRM response code: {payload.get('code')}"
            continue
        durations = payload.get("durations") or [[]]
        row_durations = durations[0] if durations else []
        if len(row_durations) != len(index):
            result.loc[index, "route_error"] = (
                f"OSRM duration count mismatch: expected {len(index)}, got {len(row_durations)}"
            )
            continue

        for row_index, duration_seconds in zip(index, row_durations, strict=True):
            result.at[row_index, "route_provider"] = provider
            result.at[row_index, "route_source_url"] = source_url
            result.at[row_index, "route_retrieved_at_utc"] = retrieved_at
            result.at[row_index, "review_status"] = review_status
            if duration_seconds is None:
                result.at[row_index, "travel_time_minutes"] = ""
                result.at[row_index, "route_status"] = "unreachable"
                result.at[row_index, "route_error"] = "OSRM returned no route."
            else:
                result.at[row_index, "travel_time_minutes"] = round(
                    float(duration_seconds) / 60,
                    2,
                )
                result.at[row_index, "route_status"] = "routed"
                result.at[row_index, "route_error"] = ""
        if request_delay_seconds:
            time.sleep(request_delay_seconds)
    return result[TRAVEL_TIME_REVIEW_COLUMNS]


def fill_travel_time_review_from_openrouteservice(
    frame: pd.DataFrame,
    *,
    api_key: str,
    base_url: str = DEFAULT_ORS_BASE_URL,
    profile: str = DEFAULT_ORS_PROFILE,
    timeout: int = 60,
    user_agent: str = DEFAULT_ROUTE_USER_AGENT,
    review_status: str = "needs_review",
    request_delay_seconds: float = 0,
    session: Any | None = None,
) -> pd.DataFrame:
    """Fill a route-review worklist from the OpenRouteService Matrix endpoint.

    OpenRouteService returns matrix durations in seconds. The resulting rows remain draft routing
    candidates until provider terms, quota limits, network vintage, profile, and row-level outputs
    are reviewed.
    """
    require_columns(frame, set(TRAVEL_TIME_REVIEW_COLUMNS), "travel time review")
    cleaned_key = api_key.strip()
    if not cleaned_key:
        raise ValueError("api_key must not be blank")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if request_delay_seconds < 0:
        raise ValueError("request_delay_seconds must be nonnegative")
    cleaned_profile = profile.strip("/")
    if not cleaned_profile:
        raise ValueError("profile must not be blank")

    result = frame.copy()
    for column in [
        "travel_time_minutes",
        "route_status",
        "route_provider",
        "route_source_url",
        "route_retrieved_at_utc",
        "route_error",
        "review_status",
    ]:
        result[column] = result[column].astype("object")
    for column in ["point_id", "facility_id", "route_status", "review_status"]:
        result[column] = result[column].astype(str).str.strip()
    _require_unique_pairs(result)
    _reset_route_output_columns(result)

    provider = f"openrouteservice:{cleaned_profile}"
    endpoint_base = base_url.rstrip("/")
    source_url = f"{endpoint_base}/v2/matrix/{quote(cleaned_profile)}"
    http = session or requests.Session()
    headers = {
        "Authorization": cleaned_key,
        "Content-Type": "application/json",
    }
    if user_agent:
        headers["User-Agent"] = user_agent
    retrieved_at = datetime.now(UTC).isoformat()

    for _, group in result.groupby("point_id", sort=False):
        index = group.index
        origin = group.iloc[0]
        coordinates = [
            _format_ors_coordinate(origin["point_longitude"], origin["point_latitude"])
        ]
        coordinates.extend(
            _format_ors_coordinate(row.facility_longitude, row.facility_latitude)
            for row in group.itertuples(index=False)
        )
        payload: dict[str, Any] = {
            "locations": coordinates,
            "sources": ["0"],
            "destinations": [str(i) for i in range(1, len(coordinates))],
            "metrics": ["duration"],
        }
        try:
            response = http.post(source_url, json=payload, timeout=timeout, headers=headers)
            response.raise_for_status()
            route_payload = response.json()
        except Exception as exc:  # pragma: no cover - exact requests exceptions vary by version
            result.loc[index, "route_error"] = f"OpenRouteService request failed: {exc}"
            continue

        if "error" in route_payload:
            result.loc[index, "route_error"] = (
                f"OpenRouteService response error: {route_payload['error']}"
            )
            continue
        durations = route_payload.get("durations") or [[]]
        row_durations = durations[0] if durations else []
        if len(row_durations) != len(index):
            result.loc[index, "route_error"] = (
                "OpenRouteService duration count mismatch: "
                f"expected {len(index)}, got {len(row_durations)}"
            )
            continue

        for row_index, duration_seconds in zip(index, row_durations, strict=True):
            result.at[row_index, "route_provider"] = provider
            result.at[row_index, "route_source_url"] = source_url
            result.at[row_index, "route_retrieved_at_utc"] = retrieved_at
            result.at[row_index, "review_status"] = review_status
            if duration_seconds is None:
                result.at[row_index, "travel_time_minutes"] = ""
                result.at[row_index, "route_status"] = "unreachable"
                result.at[row_index, "route_error"] = "OpenRouteService returned no route."
            else:
                result.at[row_index, "travel_time_minutes"] = round(
                    float(duration_seconds) / 60,
                    2,
                )
                result.at[row_index, "route_status"] = "routed"
                result.at[row_index, "route_error"] = ""
        if request_delay_seconds:
            time.sleep(request_delay_seconds)
    return result[TRAVEL_TIME_REVIEW_COLUMNS]


def _require_unique_pairs(frame: pd.DataFrame) -> None:
    duplicate_mask = frame.duplicated(["point_id", "facility_id"])
    if duplicate_mask.any():
        examples = frame.loc[duplicate_mask, ["point_id", "facility_id"]].head(5)
        raise ValueError(
            "travel time review contains duplicate point/facility pairs: "
            + examples.to_dict(orient="records").__repr__()
        )


def _reset_route_output_columns(frame: pd.DataFrame) -> None:
    defaults = {
        "travel_time_minutes": "",
        "route_status": "needs_route",
        "route_provider": "",
        "route_source_url": "",
        "route_retrieved_at_utc": "",
        "route_error": "",
        "review_status": "needs_review",
    }
    for column, value in defaults.items():
        frame[column] = pd.Series([value] * len(frame), index=frame.index, dtype="object")


def _format_osrm_coordinate(longitude: object, latitude: object) -> str:
    return f"{float(str(longitude)):.8f},{float(str(latitude)):.8f}"


def _format_ors_coordinate(longitude: object, latitude: object) -> list[float]:
    return [float(str(longitude)), float(str(latitude))]
