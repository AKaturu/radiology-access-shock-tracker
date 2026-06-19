import pandas as pd
import pytest

from radshock.sensitivity import run_sensitivity_analysis


def test_sensitivity_analysis_keeps_baseline_scores_and_ranks() -> None:
    result = run_sensitivity_analysis(_county_shocks())
    baseline = result[result["scenario_id"] == "baseline"].sort_values("county_fips")
    assert baseline["sensitivity_shock_score"].tolist() == [24.4, 28.5]
    assert baseline["score_delta_from_baseline"].tolist() == [0.0, 0.0]
    assert baseline["rank_delta_from_baseline"].tolist() == [0, 0]


def test_threshold_heavy_scenario_changes_score_emphasis() -> None:
    result = run_sensitivity_analysis(_county_shocks())
    threshold = result[result["scenario_id"] == "threshold_heavy"]
    alpha = threshold[threshold["county_fips"] == "37001"].iloc[0]
    beta = threshold[threshold["county_fips"] == "37003"].iloc[0]
    assert beta["sensitivity_shock_score"] > beta["baseline_shock_score"]
    assert alpha["sensitivity_shock_score"] < alpha["baseline_shock_score"]


def test_sensitivity_analysis_accepts_travel_time_components() -> None:
    frame = _county_shocks().rename(
        columns={
            "shock_mean_distance_component": "shock_mean_travel_time_component",
            "shock_p90_distance_component": "shock_p90_travel_time_component",
        }
    )
    result = run_sensitivity_analysis(frame)
    assert set(result["access_metric"]) == {"travel_time_minutes"}


def test_sensitivity_analysis_rejects_missing_access_components() -> None:
    frame = _county_shocks().drop(
        columns=["shock_mean_distance_component", "shock_p90_distance_component"]
    )
    with pytest.raises(ValueError, match="distance or travel-time shock component"):
        run_sensitivity_analysis(frame)


def _county_shocks() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "county_fips": "37001",
                "county_name": "Alpha",
                "shock_score": 24.4,
                "alert_level": "WARNING",
                "shock_mean_distance_component": 0.5,
                "shock_p90_distance_component": 0.2,
                "shock_threshold_component": 0.1,
                "vulnerability_poverty_component": 0.2,
                "vulnerability_rurality_component": 0.4,
                "vulnerability_risk_component": 0.3,
            },
            {
                "county_fips": "37003",
                "county_name": "Beta",
                "shock_score": 28.5,
                "alert_level": "WARNING",
                "shock_mean_distance_component": 0.2,
                "shock_p90_distance_component": 0.2,
                "shock_threshold_component": 0.8,
                "vulnerability_poverty_component": 0.5,
                "vulnerability_rurality_component": 0.4,
                "vulnerability_risk_component": 0.2,
            },
        ]
    )
