from __future__ import annotations

import hashlib

import pandas as pd

from radshock.candidates import CANDIDATE_REVIEW_COLUMNS
from radshock.schemas import require_columns

HRSA_HEALTH_CENTER_SITES_CSV_URL = (
    "https://data.hrsa.gov/DataDownload/DD_Files/"
    "Health_Center_Service_Delivery_and_LookAlike_Sites.csv"
)
HRSA_HEALTH_CENTER_SITES_DOWNLOAD_PAGE = "https://data.hrsa.gov/data/download"

HRSA_HEALTH_CENTER_REQUIRED_COLUMNS = {
    "BPHC Assigned Number",
    "Site Name",
    "Site Address",
    "Site City",
    "Site State Abbreviation",
    "Site Postal Code",
    "Health Center Location Type Description",
    "Site Status Description",
    "Health Center Type Description",
    "Geocoding Artifact Address Primary X Coordinate",
    "Geocoding Artifact Address Primary Y Coordinate",
    "State and County Federal Information Processing Standard Code",
}


def build_hrsa_candidate_review_template(
    sites: pd.DataFrame,
    *,
    state: str = "NC",
    active_only: bool = True,
    service_delivery_only: bool = True,
    review_status: str = "needs_review",
) -> pd.DataFrame:
    """Build candidate assumptions from HRSA health-center service delivery sites."""
    require_columns(sites, HRSA_HEALTH_CENTER_REQUIRED_COLUMNS, "HRSA health center sites")
    result = sites.copy()
    for column in HRSA_HEALTH_CENTER_REQUIRED_COLUMNS:
        result[column] = result[column].astype(str).str.strip()

    state_filter = state.strip().upper()
    result = result[result["Site State Abbreviation"].str.upper() == state_filter].copy()
    if active_only:
        result = result[result["Site Status Description"].str.lower() == "active"].copy()
    if service_delivery_only:
        result = result[
            result["Health Center Type Description"]
            .str.lower()
            .str.contains("service delivery", regex=False)
        ].copy()
    result = result[
        result["Geocoding Artifact Address Primary X Coordinate"].ne("")
        & result["Geocoding Artifact Address Primary Y Coordinate"].ne("")
        & result["State and County Federal Information Processing Standard Code"].ne("")
    ].copy()
    result["longitude"] = pd.to_numeric(
        result["Geocoding Artifact Address Primary X Coordinate"],
        errors="raise",
    )
    result["latitude"] = pd.to_numeric(
        result["Geocoding Artifact Address Primary Y Coordinate"],
        errors="raise",
    )
    result["county_fips"] = (
        result["State and County Federal Information Processing Standard Code"]
        .astype(str)
        .str.zfill(5)
    )
    result["candidate_type"] = result["Health Center Location Type Description"].map(
        _candidate_type_from_location
    )
    result["candidate_id"] = result.apply(_hrsa_candidate_id, axis=1)
    duplicated_ids = result["candidate_id"].duplicated(keep=False)
    result.loc[duplicated_ids, "candidate_id"] = result.loc[duplicated_ids].apply(
        lambda row: f"{row['candidate_id']}-{_candidate_identity_hash(row)}",
        axis=1,
    )
    result["candidate_name"] = result["Site Name"].astype(str).str.strip()
    result["assumption_source"] = "HRSA Health Center Service Delivery and Look-Alike Sites"
    result["review_notes"] = result.apply(_candidate_review_notes, axis=1)
    result["review_status"] = review_status.strip().lower()
    return result[CANDIDATE_REVIEW_COLUMNS].sort_values("candidate_id").reset_index(drop=True)


def _candidate_type_from_location(value: object) -> str:
    normalized = str(value).strip().lower()
    if "mobile" in normalized:
        return "mobile_stop_assumption"
    if "seasonal" in normalized:
        return "seasonal_fixed_site_assumption"
    return "fixed_site_assumption"


def _hrsa_candidate_id(row: pd.Series) -> str:
    assigned_number = str(row.get("BPHC Assigned Number", "")).strip()
    if assigned_number:
        return "HRSA-HCSD-" + assigned_number.replace(" ", "-").upper()
    key = "|".join(
        str(row.get(column, "")).strip().upper()
        for column in [
            "Site Name",
            "Site Address",
            "Site City",
            "Site State Abbreviation",
            "Site Postal Code",
        ]
    )
    return "HRSA-HCSD-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:12].upper()


def _candidate_identity_hash(row: pd.Series) -> str:
    key = "|".join(
        str(row.get(column, "")).strip().upper()
        for column in [
            "Site Name",
            "Site Address",
            "Site City",
            "Site State Abbreviation",
            "Site Postal Code",
            "Geocoding Artifact Address Primary X Coordinate",
            "Geocoding Artifact Address Primary Y Coordinate",
        ]
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:8].upper()


def _candidate_review_notes(row: pd.Series) -> str:
    address = ", ".join(
        value
        for value in [
            str(row.get("Site Address", "")).strip(),
            str(row.get("Site City", "")).strip(),
            str(row.get("Site State Abbreviation", "")).strip(),
            str(row.get("Site Postal Code", "")).strip(),
        ]
        if value
    )
    location_type = str(row.get("Health Center Location Type Description", "")).strip()
    health_center_type = str(row.get("Health Center Type Description", "")).strip()
    status = str(row.get("Site Status Description", "")).strip()
    return (
        "Reviewed HRSA-supported health center site as a planning candidate; "
        f"health_center_type={health_center_type}; location_type={location_type}; "
        f"status={status}; address={address}. "
        "This is not a claim that the site currently provides mammography."
    )
