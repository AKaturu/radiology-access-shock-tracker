from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

FACILITY_COLUMNS = {
    "facility_id",
    "facility_name",
    "latitude",
    "longitude",
    "annual_capacity",
    "active",
}

FACILITY_REQUIRED_COLUMNS = FACILITY_COLUMNS - {"annual_capacity"}

COUNTY_COLUMNS = {
    "county_fips",
    "county_name",
    "state",
    "centroid_lat",
    "centroid_lon",
    "eligible_population",
    "poverty_pct",
    "rurality_index",
    "high_risk_index",
}

POPULATION_POINT_COLUMNS = {
    "point_id",
    "county_fips",
    "latitude",
    "longitude",
    "weight",
}

CANDIDATE_COLUMNS = {
    "candidate_id",
    "candidate_name",
    "county_fips",
    "latitude",
    "longitude",
}
CANDIDATE_REVIEW_APPROVED_STATUSES = {"reviewed", "verified", "approved"}

UTILIZATION_COLUMNS = {
    "period",
    "county_fips",
    "screening_services",
    "eligible_beneficiaries",
}

TRAVEL_TIME_MATRIX_COLUMNS = {
    "point_id",
    "facility_id",
    "travel_time_minutes",
}


def require_columns(frame: pd.DataFrame, required: Iterable[str], label: str) -> None:
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise ValueError(f"{label} is missing required columns: {', '.join(missing)}")


def validate_facilities(frame: pd.DataFrame) -> pd.DataFrame:
    require_columns(frame, FACILITY_REQUIRED_COLUMNS, "facilities")
    result = frame.copy()
    if "annual_capacity" not in result.columns:
        result["annual_capacity"] = pd.NA
    result["facility_id"] = result["facility_id"].astype(str)
    result["facility_name"] = result["facility_name"].astype(str)
    result["latitude"] = pd.to_numeric(result["latitude"], errors="raise")
    result["longitude"] = pd.to_numeric(result["longitude"], errors="raise")
    result["annual_capacity"] = pd.to_numeric(result["annual_capacity"], errors="coerce")
    result["active"] = result["active"].map(_coerce_bool)
    if result["facility_id"].duplicated().any():
        duplicates = result.loc[result["facility_id"].duplicated(), "facility_id"].tolist()
        raise ValueError(f"facilities contains duplicate facility_id values: {duplicates}")
    if not result["latitude"].between(-90, 90).all():
        raise ValueError("facility latitude must be between -90 and 90")
    if not result["longitude"].between(-180, 180).all():
        raise ValueError("facility longitude must be between -180 and 180")
    return result.sort_values("facility_id").reset_index(drop=True)


def validate_counties(frame: pd.DataFrame) -> pd.DataFrame:
    require_columns(frame, COUNTY_COLUMNS, "counties")
    result = frame.copy()
    result["county_fips"] = result["county_fips"].astype(str).str.zfill(5)
    for column in [
        "centroid_lat",
        "centroid_lon",
        "eligible_population",
        "poverty_pct",
        "rurality_index",
        "high_risk_index",
    ]:
        result[column] = pd.to_numeric(result[column], errors="raise")
    if result["county_fips"].duplicated().any():
        raise ValueError("counties contains duplicate county_fips values")
    return result.sort_values("county_fips").reset_index(drop=True)


def validate_population_points(frame: pd.DataFrame) -> pd.DataFrame:
    require_columns(frame, POPULATION_POINT_COLUMNS, "population points")
    result = frame.copy()
    result["point_id"] = result["point_id"].astype(str)
    result["county_fips"] = result["county_fips"].astype(str).str.zfill(5)
    for column in ["latitude", "longitude", "weight"]:
        result[column] = pd.to_numeric(result[column], errors="raise")
    if (result["weight"] < 0).any():
        raise ValueError("population point weights must be nonnegative")
    return result.sort_values("point_id").reset_index(drop=True)


def validate_candidates(frame: pd.DataFrame) -> pd.DataFrame:
    require_columns(frame, CANDIDATE_COLUMNS, "candidates")
    result = frame.copy()
    if "review_status" in result.columns:
        review_status = result["review_status"].astype(str).str.strip().str.lower()
        invalid_review = ~review_status.isin(CANDIDATE_REVIEW_APPROVED_STATUSES)
        if invalid_review.any():
            examples = result.loc[
                invalid_review,
                ["candidate_id", "candidate_name", "review_status"],
            ].head(5)
            raise ValueError(
                "candidate review_status contains unapproved rows: "
                + examples.to_dict(orient="records").__repr__()
            )
    result["candidate_id"] = result["candidate_id"].astype(str).str.strip()
    result["candidate_name"] = result["candidate_name"].astype(str).str.strip()
    result["county_fips"] = result["county_fips"].astype(str).str.zfill(5)
    result["latitude"] = pd.to_numeric(result["latitude"], errors="raise")
    result["longitude"] = pd.to_numeric(result["longitude"], errors="raise")
    if result["candidate_id"].eq("").any():
        raise ValueError("candidate_id must not be blank")
    if result["candidate_name"].eq("").any():
        raise ValueError("candidate_name must not be blank")
    if result["candidate_id"].duplicated().any():
        duplicates = result.loc[result["candidate_id"].duplicated(), "candidate_id"].tolist()
        raise ValueError(f"candidates contains duplicate candidate_id values: {duplicates}")
    if not result["latitude"].between(-90, 90).all():
        raise ValueError("candidate latitude must be between -90 and 90")
    if not result["longitude"].between(-180, 180).all():
        raise ValueError("candidate longitude must be between -180 and 180")
    return result.sort_values("candidate_id").reset_index(drop=True)


def validate_travel_time_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    require_columns(frame, TRAVEL_TIME_MATRIX_COLUMNS, "travel time matrix")
    result = frame.copy()
    result["point_id"] = result["point_id"].astype(str)
    result["facility_id"] = result["facility_id"].astype(str)
    result["travel_time_minutes"] = pd.to_numeric(
        result["travel_time_minutes"], errors="raise"
    )
    if (result["travel_time_minutes"] < 0).any():
        raise ValueError("travel_time_minutes must be nonnegative")
    duplicate_mask = result.duplicated(["point_id", "facility_id"])
    if duplicate_mask.any():
        duplicates = (
            result.loc[duplicate_mask, ["point_id", "facility_id"]]
            .astype(str)
            .agg(" -> ".join, axis=1)
            .tolist()
        )
        raise ValueError(
            "travel time matrix contains duplicate point/facility pairs: "
            f"{duplicates}"
        )
    return result.sort_values(["point_id", "facility_id"]).reset_index(drop=True)


def _coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise ValueError(f"cannot interpret {value!r} as a boolean")
