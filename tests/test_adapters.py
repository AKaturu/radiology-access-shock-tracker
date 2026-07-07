import io
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from radshock.adapters.acs import (
    build_county_analysis_context,
    build_nc_county_analysis_context,
    build_nc_tract_analysis_context,
    to_analysis_counties,
    to_county_centroid_population_points,
    to_tract_population_points,
)
from radshock.adapters.cms import summarize_mammography_claims
from radshock.adapters.facilities import (
    build_mqsa_review_template,
    carry_forward_mqsa_review,
    finalize_mqsa_review,
    normalize_manual_facility_export,
    read_fda_mqsa_fixed_width,
)
from radshock.adapters.hrsa import build_hrsa_candidate_review_template
from radshock.adapters.places import fetch_mammography, fetch_nc_mammography
from radshock.adapters.svi import SVI_COUNTY_COLUMNS, read_svi_county_context
from radshock.states import StateScope, resolve_state_scope


def test_manual_facility_export_requires_explicit_active() -> None:
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
    assert "measureid='MAMMOUSE'" in calls[0]["params"]["$where"]


def test_places_adapter_can_fetch_all_50_states(monkeypatch: pytest.MonkeyPatch) -> None:
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
                },
                {
                    "year": "2024",
                    "stateabbr": "SC",
                    "locationname": "Other County",
                    "locationid": "45001",
                    "measure": "Mammogram use among women aged 50-74 years",
                    "data_value": "70.2",
                    "data_value_type": "Age-adjusted prevalence",
                },
                {
                    "year": "2024",
                    "stateabbr": "PR",
                    "locationname": "Puerto Rico County",
                    "locationid": "72001",
                    "measure": "Mammogram use among women aged 50-74 years",
                    "data_value": "69.2",
                    "data_value_type": "Age-adjusted prevalence",
                },
            ]

    calls: list[dict[str, object]] = []

    def fake_get(url: str, **kwargs: object) -> Response:
        calls.append({"url": url, **kwargs})
        return Response()

    monkeypatch.setattr("radshock.adapters.places.requests.get", fake_get)
    result = fetch_mammography(state="ALL", timeout=5)

    assert set(result["stateabbr"]) == {"NC", "SC"}
    assert "$limit" in calls[0]["params"]
    assert "stateabbr='NC'" not in calls[0]["params"]["$where"]
    assert "measureid='MAMMOUSE'" in calls[0]["params"]["$where"]


def test_svi_county_context_filters_to_all_50_states(tmp_path: Path) -> None:
    source = tmp_path / "svi_counties.csv"
    rows = [
        _svi_county_row("NC", "37001", "Alamance County", overall="0.25"),
        _svi_county_row("SC", "45001", "Abbeville County", overall="-999"),
        _svi_county_row("PR", "72001", "Adjuntas Municipio", overall="0.95"),
    ]
    pd.DataFrame(rows).to_csv(source, index=False)

    result = read_svi_county_context(source, state="ALL")

    assert set(result["state"]) == {"NC", "SC"}
    assert list(result["county_fips"]) == ["37001", "45001"]
    assert result.loc[result["county_fips"] == "37001", "svi_overall_percentile"].item() == 0.25
    assert pd.isna(
        result.loc[result["county_fips"] == "45001", "svi_overall_percentile"].item()
    )


def _svi_county_row(
    state: str,
    county_fips: str,
    county_name: str,
    *,
    overall: str,
) -> dict[str, str]:
    row = {column: "1" for column in SVI_COUNTY_COLUMNS}
    row.update(
        {
            "ST_ABBR": state,
            "FIPS": county_fips,
            "COUNTY": county_name,
            "LOCATION": f"{county_name}, {state}",
            "RPL_THEMES": overall,
        }
    )
    return row


def test_state_scope_accepts_all_50_and_fips() -> None:
    all_scope = resolve_state_scope("ALL")
    nc_scope = resolve_state_scope("37")

    assert all_scope.is_all_50_states
    assert len(all_scope.states) == 51
    assert "NC" in all_scope.states
    assert "CA" in all_scope.states
    assert "DC" in all_scope.states
    assert nc_scope.states == ("NC",)
    assert nc_scope.state_fips == ("37",)


def test_acs_builds_analysis_counties_and_population_points(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Response:
        def __init__(self, payload: list[list[str]] | None = None, text: str = "") -> None:
            self.payload = payload
            self.text = text

        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[list[str]]:
            assert self.payload is not None
            return self.payload

    calls: list[dict[str, object]] = []
    acs_payload = [
        [
            "NAME",
            "B01001_001E",
            "B01001_040E",
            "B01001_041E",
            "B01001_042E",
            "B01001_043E",
            "B01001_044E",
            "B01001_045E",
            "B01001_046E",
            "B17001_002E",
            "B17001_001E",
            "B08201_002E",
            "B08201_001E",
            "state",
            "county",
        ],
        [
            "County A, North Carolina",
            "10000",
            "100",
            "110",
            "50",
            "60",
            "40",
            "45",
            "55",
            "1200",
            "9500",
            "300",
            "4000",
            "37",
            "001",
        ],
        [
            "County B, North Carolina",
            "20000",
            "200",
            "210",
            "80",
            "90",
            "70",
            "75",
            "85",
            "1800",
            "19000",
            "900",
            "8000",
            "37",
            "003",
        ],
    ]
    gazetteer = "\n".join(
        [
            "USPS\tGEOID\tGEOIDFQ\tANSICODE\tNAME\tALAND\tAWATER\tALAND_SQMI\tAWATER_SQMI\tINTPTLAT\tINTPTLONG",
            "NC\t37001\t0500000US37001\t01000001\tCounty A\t100\t0\t100.0\t0\t35.1\t-78.1",
            "NC\t37003\t0500000US37003\t01000003\tCounty B\t200\t0\t50.0\t0\t36.2\t-79.2",
        ]
    )

    def fake_get(url: str, **kwargs: object) -> Response:
        calls.append({"url": url, **kwargs})
        if "api.census.gov" in url:
            return Response(payload=acs_payload)
        return Response(text=gazetteer)

    monkeypatch.setattr("radshock.adapters.acs.requests.get", fake_get)
    context = build_nc_county_analysis_context(year=2024, api_key="key", timeout=5)
    counties = to_analysis_counties(context)
    points = to_county_centroid_population_points(context)

    assert counties.loc[0, "eligible_population"] == 460
    assert counties.loc[0, "county_name"] == "County A"
    assert counties.loc[0, "poverty_pct"] == pytest.approx(12.631579, rel=1e-6)
    assert counties.loc[0, "rurality_index"] == 1
    assert counties.loc[1, "rurality_index"] == 0
    assert counties.loc[0, "high_risk_index"] == 0
    assert counties.loc[1, "high_risk_index"] == 1
    assert points.loc[0, "point_id"] == "county-37001"
    assert points.loc[0, "weight"] == 460
    assert calls[0]["params"]["key"] == "key"


def test_acs_builds_all_state_county_context(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        def __init__(
            self,
            payload: list[list[str]] | None = None,
            text: str = "",
            content: bytes = b"",
        ) -> None:
            self.payload = payload
            self.text = text
            self.content = content

        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[list[str]]:
            assert self.payload is not None
            return self.payload

    scope = StateScope(
        requested="ALL",
        states=("NC", "SC"),
        state_fips=("37", "45"),
        is_all_50_states=True,
    )
    monkeypatch.setattr("radshock.adapters.acs.resolve_state_scope", lambda _value: scope)
    calls: list[dict[str, object]] = []
    header = [
        "NAME",
        "B01001_001E",
        "B01001_040E",
        "B01001_041E",
        "B01001_042E",
        "B01001_043E",
        "B01001_044E",
        "B01001_045E",
        "B01001_046E",
        "B17001_002E",
        "B17001_001E",
        "B08201_002E",
        "B08201_001E",
        "state",
        "county",
    ]
    payloads = {
        "state:37": [
            header,
            [
                "County A, North Carolina",
                "10000",
                "100",
                "110",
                "50",
                "60",
                "40",
                "45",
                "55",
                "1200",
                "9500",
                "300",
                "4000",
                "37",
                "001",
            ],
        ],
        "state:45": [
            header,
            [
                "County C, South Carolina",
                "12000",
                "120",
                "130",
                "60",
                "70",
                "50",
                "55",
                "65",
                "1000",
                "10000",
                "500",
                "5000",
                "45",
                "001",
            ],
        ],
    }
    gazetteer = "\n".join(
        [
            "USPS\tGEOID\tGEOIDFQ\tANSICODE\tNAME\tALAND\tAWATER\tALAND_SQMI\tAWATER_SQMI\tINTPTLAT\tINTPTLONG",
            "NC\t37001\t0500000US37001\t01000001\tCounty A\t100\t0\t100.0\t0\t35.1\t-78.1",
            "SC\t45001\t0500000US45001\t01000002\tCounty C\t100\t0\t120.0\t0\t34.1\t-81.1",
            "PR\t72001\t0500000US72001\t01000003\tCounty PR\t100\t0\t50.0\t0\t18.1\t-66.1",
        ]
    )

    def fake_get(url: str, **kwargs: object) -> Response:
        calls.append({"url": url, **kwargs})
        if "api.census.gov" in url:
            params = kwargs["params"]
            return Response(payload=payloads[params["in"]])
        return Response(content=_zip_payload(gazetteer, "gazetteer.txt"))

    monkeypatch.setattr("radshock.adapters.acs.requests.get", fake_get)
    context = build_county_analysis_context(year=2024, state="ALL", api_key="key", timeout=5)

    assert set(context["state"]) == {"NC", "SC"}
    assert set(context["county_fips"]) == {"37001", "45001"}
    assert len([call for call in calls if "api.census.gov" in call["url"]]) == 2
    assert len(context) == 2


def test_acs_builds_tract_population_points(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        def __init__(self, payload: list[list[str]] | None = None, text: str = "") -> None:
            self.payload = payload
            self.text = text

        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[list[str]]:
            assert self.payload is not None
            return self.payload

    calls: list[dict[str, object]] = []
    acs_payload = [
        [
            "NAME",
            "B01001_001E",
            "B01001_040E",
            "B01001_041E",
            "B01001_042E",
            "B01001_043E",
            "B01001_044E",
            "B01001_045E",
            "B01001_046E",
            "B17001_002E",
            "B17001_001E",
            "B08201_002E",
            "B08201_001E",
            "state",
            "county",
            "tract",
        ],
        [
            "Census Tract 201, County A, North Carolina",
            "1000",
            "10",
            "11",
            "5",
            "6",
            "4",
            "4",
            "6",
            "120",
            "950",
            "30",
            "400",
            "37",
            "001",
            "020100",
        ],
        [
            "Census Tract 202, County A, North Carolina",
            "500",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "0",
            "80",
            "490",
            "20",
            "200",
            "37",
            "001",
            "020200",
        ],
    ]
    gazetteer = "\n".join(
        [
            "USPS\tGEOID\tGEOIDFQ\tNAME\tALAND\tAWATER\tALAND_SQMI\tAWATER_SQMI\tINTPTLAT\tINTPTLONG",
            "NC\t37001020100\t1400000US37001020100\tCensus Tract 201\t100\t0\t10.0\t0\t35.1\t-78.1",
            "NC\t37001020200\t1400000US37001020200\tCensus Tract 202\t200\t0\t20.0\t0\t35.2\t-78.2",
        ]
    )

    def fake_get(url: str, **kwargs: object) -> Response:
        calls.append({"url": url, **kwargs})
        if "api.census.gov" in url:
            return Response(payload=acs_payload)
        return Response(text=gazetteer)

    monkeypatch.setattr("radshock.adapters.acs.requests.get", fake_get)
    context = build_nc_tract_analysis_context(year=2024, api_key="key", timeout=5)
    points = to_tract_population_points(context)
    points_with_zero = to_tract_population_points(context, include_zero_weight=True)

    assert context.loc[0, "tract_geoid"] == "37001020100"
    assert context.loc[0, "eligible_population"] == 46
    assert context.loc[0, "county_fips"] == "37001"
    assert points.loc[0, "point_id"] == "tract-37001020100"
    assert points.loc[0, "weight"] == 46
    assert len(points) == 1
    assert len(points_with_zero) == 2
    assert calls[0]["params"]["for"] == "tract:*"
    assert calls[0]["params"]["in"] == "state:37 county:*"


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


def test_hrsa_sites_build_real_candidate_assumptions() -> None:
    sites = pd.DataFrame(
        [
            _hrsa_site(
                assigned_number="BPS-H80-000001",
                site_name="Demo Health Center",
                location_type="Permanent",
                county_fips="37001",
            ),
            _hrsa_site(
                assigned_number="BPS-H80-000002",
                site_name="Demo Mobile Unit",
                location_type="Mobile Van",
                county_fips="37003",
            ),
            _hrsa_site(
                assigned_number="BPS-H80-000003",
                site_name="Inactive Site",
                location_type="Permanent",
                county_fips="37005",
                status="Inactive",
            ),
            _hrsa_site(
                assigned_number="BPS-H80-000004",
                site_name="Other State Site",
                location_type="Permanent",
                state="SC",
                county_fips="45001",
            ),
            _hrsa_site(
                assigned_number="BPS-H80-000005",
                site_name="Administrative Office",
                location_type="Permanent",
                county_fips="37007",
                health_center_type="Administrative",
            ),
        ]
    )

    review = build_hrsa_candidate_review_template(
        sites,
        state="NC",
        review_status="reviewed",
    )

    assert list(review["candidate_id"]) == [
        "HRSA-HCSD-BPS-H80-000001",
        "HRSA-HCSD-BPS-H80-000002",
    ]
    assert list(review["candidate_type"]) == [
        "fixed_site_assumption",
        "mobile_stop_assumption",
    ]
    assert set(review["county_fips"]) == {"37001", "37003"}
    assert set(review["review_status"]) == {"reviewed"}
    assert "not a claim" in review.loc[0, "review_notes"]
    assert "Administrative Office" not in set(review["candidate_name"])


def test_hrsa_sites_can_include_all_50_states() -> None:
    sites = pd.DataFrame(
        [
            _hrsa_site(
                assigned_number="BPS-H80-000001",
                site_name="Demo Health Center",
                location_type="Permanent",
                county_fips="37001",
                state="NC",
            ),
            _hrsa_site(
                assigned_number="BPS-H80-000004",
                site_name="Other State Site",
                location_type="Permanent",
                county_fips="45001",
                state="SC",
            ),
            _hrsa_site(
                assigned_number="BPS-H80-000006",
                site_name="Territory Site",
                location_type="Permanent",
                county_fips="72001",
                state="PR",
            ),
        ]
    )

    review = build_hrsa_candidate_review_template(
        sites,
        state="ALL",
        review_status="reviewed",
    )

    assert set(review["county_fips"]) == {"37001", "45001"}
    assert "Territory Site" not in set(review["candidate_name"])


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


def test_carry_forward_mqsa_review_matches_source_hashes_only() -> None:
    current = _review_frame(review_status="needs_review", latitude="")
    current.loc[0, "facility_id"] = ""
    current.loc[0, "geocode_status"] = ""
    current.loc[1, :] = current.loc[0, :]
    current.loc[1, "source_record_hash"] = "new-hash"
    previous = _review_frame()
    previous.loc[0, "geocode_status"] = "matched"

    carried = carry_forward_mqsa_review(current, previous)

    assert carried.loc[0, "facility_id"] == "MQSA-NC-0001"
    assert carried.loc[0, "review_status"] == "reviewed"
    assert carried.loc[0, "geocode_status"] == "matched"
    assert carried.loc[1, "facility_id"] == ""
    assert carried.loc[1, "review_status"] == "needs_review"


def test_finalize_mqsa_review_allows_blank_capacity() -> None:
    result = finalize_mqsa_review(_review_frame(annual_capacity=""))
    assert result.loc[0, "facility_id"] == "MQSA-NC-0001"
    assert pd.isna(result.loc[0, "annual_capacity"])


def _review_frame(
    review_status: str = "reviewed",
    latitude: str = "35.7796",
    annual_capacity: str = "1000",
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "facility_id": "MQSA-NC-0001",
                "facility_name": "Demo Facility",
                "latitude": latitude,
                "longitude": "-78.6382",
                "annual_capacity": annual_capacity,
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


def _zip_payload(text: str, filename: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(filename, text)
    return buffer.getvalue()


def _hrsa_site(
    *,
    assigned_number: str,
    site_name: str,
    location_type: str,
    county_fips: str,
    state: str = "NC",
    status: str = "Active",
    health_center_type: str = "Service Delivery Site",
) -> dict[str, str]:
    return {
        "BPHC Assigned Number": assigned_number,
        "Site Name": site_name,
        "Site Address": "100 Main St",
        "Site City": "Raleigh",
        "Site State Abbreviation": state,
        "Site Postal Code": "27601",
        "Health Center Location Type Description": location_type,
        "Health Center Type Description": health_center_type,
        "Site Status Description": status,
        "Geocoding Artifact Address Primary X Coordinate": "-78.6382",
        "Geocoding Artifact Address Primary Y Coordinate": "35.7796",
        "State and County Federal Information Processing Standard Code": county_fips,
    }
