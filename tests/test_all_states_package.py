import importlib.util
from pathlib import Path
from types import ModuleType

import pandas as pd
import pytest

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
