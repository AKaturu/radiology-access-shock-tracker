from pathlib import Path

import pandas as pd
import pytest

from radshock.geocoding import (
    CensusGeocoder,
    GeocodeCache,
    GeocodeQuery,
    GeocodeResult,
    geocode_mqsa_review,
)


class FakeProvider:
    name = "fake"

    def __init__(self, result: GeocodeResult) -> None:
        self.result = result
        self.calls = 0

    def geocode(self, query: GeocodeQuery) -> GeocodeResult:
        self.calls += 1
        return self.result


def test_geocode_mqsa_review_fills_blank_coordinates() -> None:
    provider = FakeProvider(
        GeocodeResult(
            status="matched",
            provider="fake",
            latitude=35.7796,
            longitude=-78.6382,
            matched_address="100 MAIN ST, RALEIGH, NC, 27601",
            benchmark="fixture",
            source_url="fixture://geocoder",
            retrieved_at_utc="2026-06-19T00:00:00+00:00",
        )
    )
    result = geocode_mqsa_review(_review_frame(), provider)
    assert result.loc[0, "latitude"] == "35.7796"
    assert result.loc[0, "longitude"] == "-78.6382"
    assert result.loc[0, "geocode_status"] == "matched"
    assert result.loc[0, "review_status"] == "needs_review"


def test_geocode_mqsa_review_does_not_overwrite_existing_coordinates() -> None:
    provider = FakeProvider(
        GeocodeResult(
            status="matched",
            provider="fake",
            latitude=35.0,
            longitude=-79.0,
            matched_address="Different",
            benchmark="fixture",
            source_url="fixture://geocoder",
            retrieved_at_utc="2026-06-19T00:00:00+00:00",
        )
    )
    frame = _review_frame(latitude="36.0", longitude="-78.0")
    result = geocode_mqsa_review(frame, provider)
    assert result.loc[0, "latitude"] == "36.0"
    assert provider.calls == 0


def test_geocode_cache_reuses_prior_result(tmp_path: Path) -> None:
    provider = FakeProvider(
        GeocodeResult(
            status="matched",
            provider="fake",
            latitude=35.7796,
            longitude=-78.6382,
            matched_address="100 MAIN ST, RALEIGH, NC, 27601",
            benchmark="fixture",
            source_url="fixture://geocoder",
            retrieved_at_utc="2026-06-19T00:00:00+00:00",
        )
    )
    cache = GeocodeCache(tmp_path / "cache.json")
    geocode_mqsa_review(_review_frame(), provider, cache=cache)
    second = geocode_mqsa_review(
        _review_frame(),
        provider,
        cache=GeocodeCache(tmp_path / "cache.json"),
    )
    assert provider.calls == 1
    assert second.loc[0, "geocode_cached"] == "true"


def test_census_geocoder_parses_fixture_response(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "result": {
                    "addressMatches": [
                        {
                            "matchedAddress": "100 MAIN ST, RALEIGH, NC, 27601",
                            "coordinates": {"x": -78.6382, "y": 35.7796},
                        }
                    ]
                }
            }

    monkeypatch.setattr("radshock.geocoding.requests.get", lambda *args, **kwargs: Response())
    result = CensusGeocoder().geocode(
        GeocodeQuery(
            record_id="abc123",
            street="100 Main St",
            city="Raleigh",
            state="NC",
            zip_code="27601",
        )
    )
    assert result.status == "matched"
    assert result.latitude == 35.7796
    assert result.longitude == -78.6382


def _review_frame(latitude: str = "", longitude: str = "") -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "facility_id": "",
                "facility_name": "Demo Facility",
                "latitude": latitude,
                "longitude": longitude,
                "annual_capacity": "",
                "active": "",
                "review_status": "needs_review",
                "source_record_hash": "abc123",
                "source_name": "fda-mqsa-public",
                "source_schema_version": "fda_mqsa_pipe_delimited",
                "source_facility_name": "Demo Facility",
                "source_address_1": "100 Main St",
                "source_city": "Raleigh",
                "source_state": "NC",
                "source_zip_code": "27601",
            }
        ]
    )
