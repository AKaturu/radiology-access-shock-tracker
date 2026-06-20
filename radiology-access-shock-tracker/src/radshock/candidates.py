from __future__ import annotations

import pandas as pd

from radshock.schemas import (
    CANDIDATE_REVIEW_APPROVED_STATUSES,
    require_columns,
    validate_candidates,
    validate_counties,
)

CANDIDATE_OUTPUT_COLUMNS = [
    "candidate_id",
    "candidate_name",
    "county_fips",
    "latitude",
    "longitude",
]
CANDIDATE_REVIEW_COLUMNS = [
    "candidate_id",
    "candidate_name",
    "county_fips",
    "latitude",
    "longitude",
    "candidate_type",
    "assumption_source",
    "review_notes",
    "review_status",
]


def build_county_candidate_review_template(counties: pd.DataFrame) -> pd.DataFrame:
    """Build a review CSV for county-centroid candidate sites."""
    county_rows = validate_counties(counties)
    result = pd.DataFrame(
        {
            "candidate_id": "COUNTY-CENTROID-" + county_rows["county_fips"],
            "candidate_name": county_rows["county_name"] + " County Centroid",
            "county_fips": county_rows["county_fips"],
            "latitude": county_rows["centroid_lat"],
            "longitude": county_rows["centroid_lon"],
            "candidate_type": "county_centroid_placeholder",
            "assumption_source": "Census county Gazetteer internal point",
            "review_notes": "",
            "review_status": "needs_review",
        }
    )
    return result[CANDIDATE_REVIEW_COLUMNS].sort_values("candidate_id").reset_index(drop=True)


def finalize_candidate_review(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate reviewed candidate-site assumptions and emit analysis-ready candidates."""
    require_columns(frame, set(CANDIDATE_REVIEW_COLUMNS), "candidate review")
    result = frame.copy()
    result["review_status"] = result["review_status"].astype(str).str.strip().str.lower()
    invalid_review = ~result["review_status"].isin(CANDIDATE_REVIEW_APPROVED_STATUSES)
    if invalid_review.any():
        examples = result.loc[
            invalid_review,
            ["candidate_id", "candidate_name", "review_status"],
        ].head(5)
        raise ValueError(
            "candidate review contains rows that are not approved: "
            + examples.to_dict(orient="records").__repr__()
        )
    return validate_candidates(result[CANDIDATE_OUTPUT_COLUMNS])
