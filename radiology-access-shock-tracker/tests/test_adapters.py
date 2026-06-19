import pandas as pd
import pytest

from radshock.adapters.cms import summarize_mammography_claims
from radshock.adapters.facilities import normalize_manual_facility_export
from radshock.adapters.places import fetch_nc_mammography


def test_manual_facility_export_requires_explicit_active_and_capacity() -> None:
    frame = pd.DataFrame(
        [{"id": "F1", "name": "Facility", "lat": 35.0, "lon": -78.0, "capacity": 1000}]
    )
    with pytest.raises(ValueError, match="active"):
        normalize_manual_facility_export(frame)


def test_cms_mapping_requires_declared_columns() -> None:
    frame = pd.DataFrame([{"hcpcs": "77067", "county": "37001"}])
    with pytest.raises(ValueError, match="services"):
        summarize_mammography_claims(frame, "hcpcs", "county", "services")


def test_places_adapter_uses_fixture_response(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[dict[str, str]]:
            return [
                {
                    "year": "2024",
                    "stateabbr": "NC",
                    "locationname": "Demo County",
                    "locationid": "37001",
                    "measure": "Mammogram use among women aged 50-74 years",
                    "data_value": "71.2",
                    "data_value_type": "Age-adjusted prevalence",
                }
            ]

    calls: list[dict[str, object]] = []

    def fake_get(url: str, **kwargs: object) -> Response:
        calls.append({"url": url, **kwargs})
        return Response()

    monkeypatch.setattr("radshock.adapters.places.requests.get", fake_get)
    result = fetch_nc_mammography(timeout=5)
    assert result.loc[0, "county_fips"] == "37001"
    assert result.loc[0, "data_value"] == 71.2
    assert calls[0]["params"] is not None
