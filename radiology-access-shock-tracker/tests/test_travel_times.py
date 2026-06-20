import pandas as pd
import pytest

from radshock.travel_times import (
    build_travel_time_review_template,
    fill_travel_time_review_from_osrm,
    finalize_travel_time_review,
)


def test_build_travel_time_review_template_pairs_active_facilities_only() -> None:
    review = build_travel_time_review_template(_population(), _facilities())
    assert len(review) == 2
    assert set(review["facility_id"]) == {"F1"}
    assert set(review["route_status"]) == {"needs_route"}
    assert set(review["review_status"]) == {"needs_review"}
    assert "straight_line_miles" in review.columns


def test_build_travel_time_review_template_can_filter_by_distance() -> None:
    review = build_travel_time_review_template(
        _population(),
        _facilities(),
        max_distance_miles=1,
    )
    assert len(review) == 1
    assert review.loc[0, "point_id"] == "P1"


def test_finalize_travel_time_review_emits_only_routed_pairs() -> None:
    matrix = finalize_travel_time_review(
        pd.DataFrame(
            [
                {
                    "point_id": "P1",
                    "facility_id": "F1",
                    "travel_time_minutes": "22.5",
                    "route_status": "routed",
                    "review_status": "approved",
                },
                {
                    "point_id": "P2",
                    "facility_id": "F1",
                    "travel_time_minutes": "",
                    "route_status": "unreachable",
                    "review_status": "reviewed",
                },
            ]
        )
    )
    assert matrix.to_dict(orient="records") == [
        {"point_id": "P1", "facility_id": "F1", "travel_time_minutes": 22.5}
    ]


def test_finalize_travel_time_review_blocks_unapproved_rows() -> None:
    with pytest.raises(ValueError, match="not approved"):
        finalize_travel_time_review(
            pd.DataFrame(
                [
                    {
                        "point_id": "P1",
                        "facility_id": "F1",
                        "travel_time_minutes": "22.5",
                        "route_status": "routed",
                        "review_status": "needs_review",
                    }
                ]
            )
        )


def test_finalize_travel_time_review_blocks_missing_minutes_for_routed_rows() -> None:
    with pytest.raises(ValueError, match="travel_time_minutes"):
        finalize_travel_time_review(
            pd.DataFrame(
                [
                    {
                        "point_id": "P1",
                        "facility_id": "F1",
                        "travel_time_minutes": "",
                        "route_status": "routed",
                        "review_status": "approved",
                    }
                ]
            )
        )


def test_fill_travel_time_review_from_osrm_writes_minutes_and_keeps_review_pending() -> None:
    review = build_travel_time_review_template(_population(), _facilities())
    result = fill_travel_time_review_from_osrm(
        review,
        base_url="https://router.example.test",
        timeout=10,
        user_agent="radshock-test",
        session=_FakeSession(
            [
                [600.0],
                [None],
            ]
        ),
    )

    assert result.loc[0, "travel_time_minutes"] == 10.0
    assert result.loc[0, "route_status"] == "routed"
    assert result.loc[0, "route_provider"] == "osrm:driving"
    assert result.loc[0, "route_source_url"] == "https://router.example.test/table/v1/driving"
    assert result.loc[0, "review_status"] == "needs_review"
    assert result.loc[1, "travel_time_minutes"] == ""
    assert result.loc[1, "route_status"] == "unreachable"
    assert result.loc[1, "route_error"] == "OSRM returned no route."


def test_fill_travel_time_review_from_osrm_allows_explicit_review_status() -> None:
    review = build_travel_time_review_template(_population(), _facilities())
    result = fill_travel_time_review_from_osrm(
        review,
        review_status="reviewed",
        session=_FakeSession(
            [
                [120.0],
                [240.0],
            ]
        ),
    )

    assert set(result["review_status"]) == {"reviewed"}


class _FakeSession:
    def __init__(self, duration_rows: list[list[float | None]]) -> None:
        self.duration_rows = duration_rows
        self.calls: list[dict[str, object]] = []

    def get(self, url: str, timeout: int, headers: dict[str, str]) -> "_FakeResponse":
        self.calls.append({"url": url, "timeout": timeout, "headers": headers})
        return _FakeResponse(self.duration_rows.pop(0))


class _FakeResponse:
    def __init__(self, durations: list[float | None]) -> None:
        self.durations = durations

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return {"code": "Ok", "durations": [self.durations]}


def _population() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["P1", "37001", 35.0, -78.0, 100],
            ["P2", "37001", 36.0, -79.0, 50],
        ],
        columns=["point_id", "county_fips", "latitude", "longitude", "weight"],
    )


def _facilities() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["F1", "Active Facility", 35.0, -78.0, 1000, True],
            ["F2", "Inactive Facility", 35.1, -78.1, 1000, False],
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
