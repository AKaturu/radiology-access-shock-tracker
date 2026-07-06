from __future__ import annotations

import pandas as pd
import pytest

from radshock.causal import build_causal_study_exports


def test_build_causal_study_exports_multiple_periods() -> None:
    county_panel, period_panel = build_causal_study_exports(
        _utilization(),
        _shocks(),
        pre_periods=["2024Q1", "2024Q2"],
        post_periods=["2025Q1", "2025Q2"],
    )

    alpha = county_panel[county_panel["county_fips"] == "37001"].iloc[0]
    assert alpha["periods_observed_pre"] == 2
    assert alpha["periods_observed_post"] == 2
    assert alpha["exposure_group"] == "higher_shock"
    assert alpha["rate_delta_per_1000"] == 30
    assert set(period_panel["study_phase"]) == {"pre", "post"}


def test_build_causal_study_exports_rejects_overlapping_periods() -> None:
    with pytest.raises(ValueError, match="both pre and post"):
        build_causal_study_exports(
            _utilization(),
            _shocks(),
            pre_periods=["2024Q1"],
            post_periods=["2024Q1"],
        )


def _utilization() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["2024Q1", "37001", 100, 1000],
            ["2024Q2", "37001", 120, 1000],
            ["2025Q1", "37001", 130, 1000],
            ["2025Q2", "37001", 150, 1000],
            ["2024Q1", "37003", 80, 1000],
            ["2025Q1", "37003", 90, 1000],
        ],
        columns=["period", "county_fips", "screening_services", "eligible_beneficiaries"],
    )


def _shocks() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["37001", "Alpha", 25.0, "WARNING"],
            ["37003", "Beta", 1.0, "NONE"],
        ],
        columns=["county_fips", "county_name", "shock_score", "alert_level"],
    )
