import pandas as pd
import pytest

from radshock.candidates import build_county_candidate_review_template, finalize_candidate_review


def test_build_county_candidate_review_template_requires_review() -> None:
    review = build_county_candidate_review_template(_counties())

    assert review.loc[0, "candidate_id"] == "COUNTY-CENTROID-37001"
    assert review.loc[0, "candidate_type"] == "county_centroid_placeholder"
    assert review.loc[0, "review_status"] == "needs_review"


def test_finalize_candidate_review_blocks_unapproved_rows() -> None:
    with pytest.raises(ValueError, match="not approved"):
        finalize_candidate_review(_review_frame(review_status="needs_review"))


def test_finalize_candidate_review_outputs_analysis_ready_candidates() -> None:
    result = finalize_candidate_review(_review_frame(review_status="reviewed"))

    assert list(result.columns) == [
        "candidate_id",
        "candidate_name",
        "county_fips",
        "latitude",
        "longitude",
    ]
    assert result.loc[0, "candidate_id"] == "C1"
    assert result.loc[0, "county_fips"] == "37001"


def _counties() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["37001", "Alamance", "NC", 36.04, -79.39, 1000, 10.0, 0.2, 0.3],
        ],
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


def _review_frame(review_status: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "candidate_id": "C1",
                "candidate_name": "Reviewed Stop",
                "county_fips": "37001",
                "latitude": "36.04",
                "longitude": "-79.39",
                "candidate_type": "mobile_stop",
                "assumption_source": "reviewed planning source",
                "review_notes": "",
                "review_status": review_status,
            }
        ]
    )
