import pandas as pd
import pytest

from radshock.travel_times import (
    build_travel_time_review_template,
    fill_travel_time_review_from_openrouteservice,
    fill_travel_time_review_from_osrm,
    finalize_travel_time_review,
    limit_travel_time_review_origins,
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


def test_build_travel_time_review_template_can_cap_nearest_facilities() -> None:
    review = build_travel_time_review_template(
        _population(),
        _many_active_facilities(),
        max_facilities_per_point=2,
    )

    assert len(review) == 4
    assert set(review.groupby("point_id")["facility_id"].count()) == {2}
    first_point = review[review["point_id"] == "P1"]
    assert list(first_point["facility_id"]) == ["F1", "F2"]


def test_build_travel_time_review_template_rejects_invalid_nearest_cap() -> None:
    with pytest.raises(ValueError, match="max_facilities_per_point"):
        build_travel_time_review_template(
            _population(),
            _many_active_facilities(),
            max_facilities_per_point=0,
        )


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


def test_limit_travel_time_review_origins_preserves_original_indexes() -> None:
    review = build_travel_time_review_template(_population(), _many_active_facilities())
    subset = limit_travel_time_review_origins(review, max_origins=1)

    assert set(subset["point_id"]) == {"P1"}
    assert list(subset.index) == [0, 1, 2]


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


def test_fill_travel_time_review_from_osrm_clears_stale_provider_rows_on_refill() -> None:
    review = build_travel_time_review_template(_population(), _facilities())
    review["travel_time_minutes"] = "99.0"
    review["route_status"] = "routed"
    review["route_provider"] = "osrm:old"
    review["route_source_url"] = "https://router.project-osrm.org/table/v1/driving"
    review["route_retrieved_at_utc"] = "2026-06-20T00:00:00+00:00"
    review["review_status"] = "reviewed"

    result = fill_travel_time_review_from_osrm(review, session=_FailingSession())

    assert set(result["travel_time_minutes"]) == {""}
    assert set(result["route_status"]) == {"needs_route"}
    assert set(result["route_provider"]) == {""}
    assert set(result["route_source_url"]) == {""}
    assert set(result["review_status"]) == {"needs_review"}
    assert result["route_error"].str.startswith("OSRM request failed").all()


def test_fill_travel_time_review_from_openrouteservice_writes_minutes_and_metadata() -> None:
    review = build_travel_time_review_template(_population(), _facilities())
    session = _FakePostSession(
        [
            [900.0],
            [None],
        ]
    )
    result = fill_travel_time_review_from_openrouteservice(
        review,
        api_key="test-key",
        base_url="https://ors.example.test",
        timeout=10,
        user_agent="radshock-test",
        session=session,
    )

    assert result.loc[0, "travel_time_minutes"] == 15.0
    assert result.loc[0, "route_status"] == "routed"
    assert result.loc[0, "route_provider"] == "openrouteservice:driving-car"
    assert result.loc[0, "route_source_url"] == "https://ors.example.test/v2/matrix/driving-car"
    assert result.loc[0, "review_status"] == "needs_review"
    assert result.loc[1, "travel_time_minutes"] == ""
    assert result.loc[1, "route_status"] == "unreachable"
    assert result.loc[1, "route_error"] == "OpenRouteService returned no route."
    assert session.calls[0]["json"] == {
        "locations": [[-78.0, 35.0], [-78.0, 35.0]],
        "sources": ["0"],
        "destinations": ["1"],
        "metrics": ["duration"],
    }
    assert session.calls[0]["headers"]["Authorization"] == "test-key"


def test_fill_travel_time_review_from_openrouteservice_blocks_blank_key() -> None:
    review = build_travel_time_review_template(_population(), _facilities())

    with pytest.raises(ValueError, match="api_key"):
        fill_travel_time_review_from_openrouteservice(review, api_key="  ")


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


class _FailingSession:
    def get(self, url: str, timeout: int, headers: dict[str, str]) -> "_FakeResponse":
        raise RuntimeError("local router unavailable")


class _FakePostSession:
    def __init__(self, duration_rows: list[list[float | None]]) -> None:
        self.duration_rows = duration_rows
        self.calls: list[dict[str, object]] = []

    def post(
        self,
        url: str,
        json: dict[str, object],
        timeout: int,
        headers: dict[str, str],
    ) -> "_FakeResponse":
        self.calls.append({"url": url, "json": json, "timeout": timeout, "headers": headers})
        return _FakeResponse(self.duration_rows.pop(0))


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


def _many_active_facilities() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["F1", "Near Facility", 35.0, -78.0, 1000, True],
            ["F2", "Second Facility", 35.1, -78.1, 1000, True],
            ["F3", "Far Facility", 37.0, -80.0, 1000, True],
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
