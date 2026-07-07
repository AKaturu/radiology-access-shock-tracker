import importlib.util
import json
from datetime import date
from pathlib import Path
from types import ModuleType

import pandas as pd
import pytest
import requests

from radshock.gates import ALL_STATES_FIPS_LIST, load_resolutions, resolve_gate
from radshock.states import US_STATE_FIPS_TO_ABBR

PACKAGE_SCRIPT = (
    Path(__file__).resolve().parents[1] / "scripts" / "build_all_states_data_package.py"
)


def _load_package_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("build_all_states_data_package", PACKAGE_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PACKAGE_MODULE = _load_package_script()


def test_state_coverage_summary_includes_public_and_acs_sources() -> None:
    summary = pd.DataFrame(
        [
            _state_row("AL"),
            _state_row("AK", hrsa_candidate_review_rows=0, acs_county_context_rows=0),
            _state_row(
                "AZ",
                mqsa_source_rows=0,
                places_mammography_rows=0,
                acs_county_context_rows=0,
                acs_tract_context_rows=0,
            ),
        ]
    )
    summary["sources_present"] = [
        6,
        5,
        4,
    ]

    coverage = PACKAGE_MODULE._state_coverage_summary(summary)
    gaps = PACKAGE_MODULE._state_coverage_gaps(summary)

    assert coverage["states"] == 3
    assert coverage["states_with_mqsa_rows"] == 2
    assert coverage["states_with_hrsa_candidates"] == 2
    assert coverage["states_with_acs_county_context"] == 1
    assert coverage["states_with_acs_tract_context"] == 2
    assert coverage["states_with_all_public_no_secret_sources"] == 1
    assert gaps["missing_mqsa_rows"] == ["AZ"]
    assert gaps["missing_hrsa_candidates"] == ["AK"]
    assert gaps["missing_places_rows"] == ["AZ"]
    assert gaps["missing_any_public_no_secret_source"] == ["AK", "AZ"]
    assert gaps["missing_acs_county_context"] == ["AK", "AZ"]


def test_render_coverage_gaps_distinguishes_public_sources_from_optional_acs() -> None:
    gaps = {
        "missing_mqsa_rows": [],
        "missing_hrsa_candidates": [],
        "missing_places_rows": [],
        "missing_census_counties": [],
        "missing_census_tracts": [],
        "missing_cdc_atsdr_svi_counties": [],
        "missing_any_public_no_secret_source": [],
        "missing_acs_county_context": ["AL", "AK"],
        "missing_acs_tract_context": ["AL", "AK"],
    }

    report = PACKAGE_MODULE._render_coverage_gaps(gaps)

    assert "Public no-secret source coverage: no state gaps detected." in report
    assert "missing_acs_county_context: AL, AK" in report
    assert "missing_acs_tract_context: AL, AK" in report


def test_required_acs_key_blocks_production_package(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="CENSUS_API_KEY is required"):
        PACKAGE_MODULE._maybe_build_acs_outputs(
            tmp_path,
            year=2024,
            force=True,
            census_api_key=None,
            require_acs=True,
        )


def test_package_readiness_gates_only_include_acs_when_incomplete() -> None:
    complete = pd.DataFrame([_state_row("AL"), _state_row("AK", state_fips="02")])
    complete["sources_present"] = 6

    complete_gates = PACKAGE_MODULE._build_package_readiness_gates(complete)

    assert not any(gate.startswith("ACS") for gate in complete_gates)

    incomplete = pd.DataFrame(
        [_state_row("AL"), _state_row("AK", state_fips="02", acs_tract_context_rows=0)]
    )
    incomplete["sources_present"] = [6, 6]

    incomplete_gates = PACKAGE_MODULE._build_package_readiness_gates(incomplete)

    assert any(
        gate.startswith("ACS county/tract context is incomplete") for gate in incomplete_gates
    )


def test_state_readiness_audit_marks_review_and_acs_gates_by_state() -> None:
    summary = pd.DataFrame(
        [
            _state_row("AL", state_fips="01"),
            _state_row("AK", state_fips="02", acs_county_context_rows=0),
        ]
    )

    audit = PACKAGE_MODULE._build_state_readiness_audit(summary)
    by_state = audit.set_index("state")

    assert by_state.loc["AL", "overall_status"] == "BLOCKED"
    assert by_state.loc["AL", "mqsa_review_status"] == "BLOCKER"
    assert by_state.loc["AL", "acs_status"] == "PASS"
    assert by_state.loc["AK", "acs_status"] == "BLOCKER"


def _state_row(
    state: str,
    *,
    state_fips: str = "01",
    mqsa_source_rows: int = 1,
    hrsa_candidate_review_rows: int = 1,
    places_mammography_rows: int = 1,
    census_counties: int = 1,
    census_tracts: int = 1,
    cdc_atsdr_svi_counties: int = 1,
    acs_county_context_rows: int = 1,
    acs_tract_context_rows: int = 1,
) -> dict[str, int | str]:
    return {
        "state": state,
        "state_fips": state_fips,
        "mqsa_source_rows": mqsa_source_rows,
        "hrsa_candidate_review_rows": hrsa_candidate_review_rows,
        "places_mammography_rows": places_mammography_rows,
        "census_counties": census_counties,
        "census_tracts": census_tracts,
        "cdc_atsdr_svi_counties": cdc_atsdr_svi_counties,
        "acs_county_context_rows": acs_county_context_rows,
        "acs_tract_context_rows": acs_tract_context_rows,
    }


def test_mark_publication_ready_rejects_unresolved_gates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mock_package_sources(monkeypatch, tmp_path)
    rp = tmp_path / "nonexistent.json"
    with pytest.raises(RuntimeError, match="Cannot mark publication ready"):
        PACKAGE_MODULE.build_all_states_data_package(
            tmp_path / "output",
            year=2024,
            force=True,
            census_api_key=None,
            require_acs=False,
            mark_publication_ready=True,
            resolutions_file=rp,
        )


def test_mark_publication_ready_accepts_when_all_gates_resolved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mock_package_sources(monkeypatch, tmp_path)
    rp = tmp_path / "resolutions.json"
    resolutions = load_resolutions(rp)
    for fips in ALL_STATES_FIPS_LIST:
        resolve_gate(
            resolutions,
            gate_name="mqsa_review",
            state=fips,
            resolved_by="@test",
            evidence="all resolved",
        )
        resolve_gate(
            resolutions,
            gate_name="hrsa_candidate_review",
            state=fips,
            resolved_by="@test",
            evidence="all resolved",
        )
        resolve_gate(
            resolutions,
            gate_name="travel_time_matrices",
            state=fips,
            resolved_by="@test",
            evidence="all resolved",
        )
    from radshock.gates import save_resolutions
    save_resolutions(resolutions, rp)

    def _fake_acs(*args, **kwargs):
        county_fips = sorted(f"{s}001" for s in ALL_STATES_FIPS_LIST)
        tract_fips = sorted(f"{s}001020100" for s in ALL_STATES_FIPS_LIST)
        return {
            "status_note": "mocked ACS",
            "paths": {},
            "row_counts": {
                "acs_county_context_rows": 50,
                "acs_tract_context_rows": 50,
                "acs_county_population_points": 50,
                "acs_tract_population_points": 50,
            },
            "counties_frame": pd.DataFrame({
                "county_fips": county_fips,
                "state": [US_STATE_FIPS_TO_ABBR[f[:2]] for f in county_fips],
                "total_population": [50000] * 50,
            }),
            "tracts_frame": pd.DataFrame({
                "tract_geoid": tract_fips,
                "county_fips": [f[:5] for f in tract_fips],
                "state": [US_STATE_FIPS_TO_ABBR[f[:2]] for f in tract_fips],
                "total_population": [5000] * 50,
            }),
        }
    monkeypatch.setattr(PACKAGE_MODULE, "_maybe_build_acs_outputs", _fake_acs)

    manifest = PACKAGE_MODULE.build_all_states_data_package(
        tmp_path / "output",
        year=2024,
        force=True,
        census_api_key=None,
        require_acs=False,
        mark_publication_ready=True,
        resolutions_file=rp,
    )

    assert manifest["publication_status"] == "ready_for_publication"
    assert manifest["readiness_gates"] == []


def test_resolutions_file_arg_passed_to_readiness_gates(tmp_path: Path) -> None:
    rp = tmp_path / "custom.json"
    rp.write_text(
        json.dumps({
            "version": 1,
            "gates": {
                "mqsa_review": {
                    "label": "MQSA review",
                    "resolved_states": {
                        fips: {"resolved_by": "@test", "resolved_at": "now", "evidence": "x"}
                        for fips in ALL_STATES_FIPS_LIST
                    },
                },
                "hrsa_candidate_review": {"label": "HRSA candidate review", "resolved_states": {}},
                "travel_time_matrices": {"label": "Travel-time matrices", "resolved_states": {}},
            },
        }) + "\n",
        encoding="utf-8",
    )

    summary = pd.DataFrame([_state_row("AL"), _state_row("AK", state_fips="02")])
    summary["sources_present"] = 6

    gates = PACKAGE_MODULE._build_package_readiness_gates(
        summary, PACKAGE_MODULE.load_resolutions(rp)
    )

    mqsa_gates = [g for g in gates if "MQSA" in g]
    assert len(mqsa_gates) == 0


def test_fetch_mqsa_archive_falls_back_to_nber_mirror(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []

    def _fake_fetch_url_source(
        url: str,
        output_dir: Path,
        source_name: str,
        **kwargs: object,
    ) -> Path:
        calls.append((url, source_name))
        if len(calls) == 1:
            raise requests.HTTPError("primary FDA blocked")
        path = tmp_path / "public.zip"
        path.write_bytes(b"mirror archive")
        return path

    monkeypatch.setattr(PACKAGE_MODULE, "fetch_url_source", _fake_fetch_url_source)

    archive, source_note = PACKAGE_MODULE._fetch_mqsa_archive(
        tmp_path,
        run_date=date(2026, 7, 6),
        force=True,
    )

    assert archive.read_bytes() == b"mirror archive"
    assert calls == [
        (PACKAGE_MODULE.FDA_MQSA_PUBLIC_ZIP_URL, "fda-mqsa-public"),
        (PACKAGE_MODULE.NBER_FDA_MQSA_PUBLIC_ZIP_URL, "nber-fda-mqsa-public-mirror"),
    ]
    assert source_note["selected_source"] == "nber_fda_mqsa_public_mirror"
    assert source_note["fallback_status"] == "downloaded"
    assert source_note["primary_status"].startswith("failed: HTTPError")


def _mock_package_sources(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    county_fips = sorted(f"{state_fips}001" for state_fips in ALL_STATES_FIPS_LIST)
    states = [US_STATE_FIPS_TO_ABBR[fips[:2]] for fips in county_fips]

    def _fake_fetch_url_source(
        url: str,
        output_dir: Path,
        source_name: str,
        **kwargs: object,
    ) -> Path:
        path = tmp_path / f"{source_name}.csv"
        path.write_text("placeholder\nvalue\n", encoding="utf-8")
        return path

    monkeypatch.setattr(PACKAGE_MODULE, "fetch_url_source", _fake_fetch_url_source)
    monkeypatch.setattr(
        PACKAGE_MODULE,
        "read_fda_mqsa_fixed_width",
        lambda *args, **kwargs: pd.DataFrame(
            {"source_state": states, "is_mobile_name_hint": [False] * len(states)}
        ),
    )
    monkeypatch.setattr(
        PACKAGE_MODULE,
        "build_mqsa_review_template",
        lambda frame: pd.DataFrame({"source_state": frame["source_state"]}),
    )
    monkeypatch.setattr(
        PACKAGE_MODULE,
        "build_hrsa_candidate_review_template",
        lambda *args, **kwargs: pd.DataFrame({"county_fips": county_fips}),
    )
    monkeypatch.setattr(
        PACKAGE_MODULE,
        "fetch_mammography",
        lambda *args, **kwargs: pd.DataFrame(
            {"stateabbr": states, "county_fips": county_fips}
        ),
    )
    monkeypatch.setattr(
        PACKAGE_MODULE,
        "fetch_county_gazetteer",
        lambda *args, **kwargs: pd.DataFrame({"county_fips": county_fips}),
    )
    monkeypatch.setattr(
        PACKAGE_MODULE,
        "fetch_tract_gazetteer",
        lambda *args, **kwargs: pd.DataFrame({"county_fips": county_fips}),
    )
    monkeypatch.setattr(
        PACKAGE_MODULE,
        "read_svi_county_context",
        lambda *args, **kwargs: pd.DataFrame({"county_fips": county_fips}),
    )
