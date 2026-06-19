import zipfile
from pathlib import Path

import pandas as pd
import pytest

from radshock.adapters.cms import summarize_mammography_claims
from radshock.adapters.facilities import (
    build_mqsa_review_template,
    finalize_mqsa_review,
    normalize_manual_facility_export,
    read_fda_mqsa_fixed_width,
)
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


def test_fda_mqsa_fixed_width_zip_builds_review_template(tmp_path: Path) -> None:
    line = _mqsa_line(
        name="Demo Mobile Mammography",
        address_1="100 Main St",
        city="Raleigh",
        state="NC",
        zip_code="27601",
        phone="919-555-0100",
    )
    zip_path = tmp_path / "public.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("public.txt", line + "\n")

    raw = read_fda_mqsa_fixed_width(zip_path, state="NC")
    review = build_mqsa_review_template(raw)

    assert raw.loc[0, "source_facility_name"] == "Demo Mobile Mammography"
    assert raw.loc[0, "is_mobile_name_hint"]
    assert review.loc[0, "facility_id"] == ""
    assert review.loc[0, "latitude"] == ""
    assert review.loc[0, "active"] == ""
    assert review.loc[0, "facility_name"] == "Demo Mobile Mammography"


def test_fda_mqsa_pipe_delimited_source_is_supported(tmp_path: Path) -> None:
    source = tmp_path / "public.txt"
    source.write_text(
        "Demo Facility|100 Main St|||Raleigh|NC|27601|9195550100|9195550101\n"
    )
    raw = read_fda_mqsa_fixed_width(source, state="NC")
    assert raw.loc[0, "source_facility_name"] == "Demo Facility"
    assert raw.loc[0, "source_state"] == "NC"
    assert raw.loc[0, "source_schema_version"] == "fda_mqsa_pipe_delimited"


def test_finalize_mqsa_review_rejects_needs_review_rows() -> None:
    review = _review_frame(review_status="needs_review")
    with pytest.raises(ValueError, match="not approved"):
        finalize_mqsa_review(review)


def test_finalize_mqsa_review_rejects_blank_coordinates() -> None:
    review = _review_frame(latitude="")
    with pytest.raises(ValueError, match="latitude blank"):
        finalize_mqsa_review(review)


def test_finalize_mqsa_review_outputs_valid_snapshot_rows() -> None:
    result = finalize_mqsa_review(_review_frame())
    assert result.loc[0, "facility_id"] == "MQSA-NC-0001"
    assert result.loc[0, "active"]
    assert result.loc[0, "source_record_hash"] == "abc123"


def _review_frame(
    review_status: str = "reviewed",
    latitude: str = "35.7796",
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "facility_id": "MQSA-NC-0001",
                "facility_name": "Demo Facility",
                "latitude": latitude,
                "longitude": "-78.6382",
                "annual_capacity": "1000",
                "active": "true",
                "review_status": review_status,
                "source_record_hash": "abc123",
                "source_name": "fda-mqsa-public",
                "source_schema_version": "fda_mqsa_pipe_delimited",
            }
        ]
    )


def _mqsa_line(
    name: str,
    address_1: str,
    city: str,
    state: str,
    zip_code: str,
    phone: str,
    address_2: str = "",
    address_3: str = "",
    fax: str = "",
) -> str:
    return (
        f"{name:<75}"
        f"{address_1:<50}"
        f"{address_2:<50}"
        f"{address_3:<50}"
        f"{city:<50}"
        f"{state:<2}"
        f"{zip_code:<15}"
        f"{phone:<50}"
        f"{fax:<50}"
    )
