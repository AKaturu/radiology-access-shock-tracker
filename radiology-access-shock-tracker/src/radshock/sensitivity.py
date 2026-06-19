from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from radshock.schemas import require_columns

AccessMetric = Literal["distance_miles", "travel_time_minutes"]

IDENTIFIER_COLUMNS = {"county_fips", "county_name", "shock_score", "alert_level"}
VULNERABILITY_COMPONENT_COLUMNS = {
    "vulnerability_poverty_component",
    "vulnerability_rurality_component",
    "vulnerability_risk_component",
}


@dataclass(frozen=True)
class WeightScenario:
    """Alternative shock-score weighting assumptions for reviewer sensitivity checks."""

    scenario_id: str
    scenario_name: str
    description: str
    mean_weight: float
    p90_weight: float
    threshold_weight: float
    poverty_weight: float
    rurality_weight: float
    risk_weight: float
    vulnerability_floor: float = 0.70
    vulnerability_multiplier: float = 0.30

    def validate(self) -> None:
        _validate_weight_sum(
            self.mean_weight + self.p90_weight + self.threshold_weight,
            f"{self.scenario_id} deterioration weights",
        )
        _validate_weight_sum(
            self.poverty_weight + self.rurality_weight + self.risk_weight,
            f"{self.scenario_id} vulnerability weights",
        )
        _validate_weight_sum(
            self.vulnerability_floor + self.vulnerability_multiplier,
            f"{self.scenario_id} vulnerability adjustment",
        )


DEFAULT_SCENARIOS = (
    WeightScenario(
        scenario_id="baseline",
        scenario_name="Baseline",
        description="Current published exploratory weighting.",
        mean_weight=0.45,
        p90_weight=0.30,
        threshold_weight=0.25,
        poverty_weight=0.40,
        rurality_weight=0.30,
        risk_weight=0.30,
    ),
    WeightScenario(
        scenario_id="mean_access_heavy",
        scenario_name="Mean Access Heavy",
        description="Places more emphasis on broad average access deterioration.",
        mean_weight=0.60,
        p90_weight=0.25,
        threshold_weight=0.15,
        poverty_weight=0.40,
        rurality_weight=0.30,
        risk_weight=0.30,
    ),
    WeightScenario(
        scenario_id="tail_access_heavy",
        scenario_name="Tail Access Heavy",
        description="Places more emphasis on 90th-percentile access deterioration.",
        mean_weight=0.25,
        p90_weight=0.50,
        threshold_weight=0.25,
        poverty_weight=0.40,
        rurality_weight=0.30,
        risk_weight=0.30,
    ),
    WeightScenario(
        scenario_id="threshold_heavy",
        scenario_name="Threshold Heavy",
        description="Places more emphasis on populations newly beyond the access threshold.",
        mean_weight=0.30,
        p90_weight=0.20,
        threshold_weight=0.50,
        poverty_weight=0.40,
        rurality_weight=0.30,
        risk_weight=0.30,
    ),
    WeightScenario(
        scenario_id="vulnerability_heavy",
        scenario_name="Vulnerability Heavy",
        description="Increases the effect of community vulnerability on the composite score.",
        mean_weight=0.45,
        p90_weight=0.30,
        threshold_weight=0.25,
        poverty_weight=0.45,
        rurality_weight=0.25,
        risk_weight=0.30,
        vulnerability_floor=0.60,
        vulnerability_multiplier=0.40,
    ),
)


def run_sensitivity_analysis(
    county_shocks: pd.DataFrame,
    scenarios: tuple[WeightScenario, ...] = DEFAULT_SCENARIOS,
) -> pd.DataFrame:
    """Re-score county shocks under alternative transparent weighting assumptions."""
    frame = _prepare_county_shocks(county_shocks)
    metric, mean_column, p90_column = _detect_access_metric(frame)
    baseline = _baseline_ranks(frame)
    outputs: list[pd.DataFrame] = []
    for scenario in scenarios:
        scenario.validate()
        scored = frame[
            ["county_fips", "county_name", "shock_score", "alert_level"]
        ].copy()
        scored["scenario_id"] = scenario.scenario_id
        scored["scenario_name"] = scenario.scenario_name
        scored["scenario_description"] = scenario.description
        scored["access_metric"] = metric
        scored["baseline_shock_score"] = frame["shock_score"].astype(float)
        scored["sensitivity_shock_score"] = _score_scenario(
            frame,
            scenario,
            mean_column,
            p90_column,
        )
        scored["score_delta_from_baseline"] = (
            scored["sensitivity_shock_score"] - scored["baseline_shock_score"]
        ).round(1)
        scored["baseline_alert_level"] = frame["alert_level"].astype(str)
        scored["sensitivity_alert_level"] = _alert_levels(scored["sensitivity_shock_score"])
        scored["baseline_rank"] = baseline["baseline_rank"]
        scored["sensitivity_rank"] = _scenario_ranks(scored)
        scored["rank_delta_from_baseline"] = (
            scored["sensitivity_rank"] - scored["baseline_rank"]
        )
        scored["mean_weight"] = scenario.mean_weight
        scored["p90_weight"] = scenario.p90_weight
        scored["threshold_weight"] = scenario.threshold_weight
        scored["poverty_weight"] = scenario.poverty_weight
        scored["rurality_weight"] = scenario.rurality_weight
        scored["risk_weight"] = scenario.risk_weight
        scored["vulnerability_floor"] = scenario.vulnerability_floor
        scored["vulnerability_multiplier"] = scenario.vulnerability_multiplier
        outputs.append(scored)
    result = pd.concat(outputs, ignore_index=True)
    return result[
        [
            "scenario_id",
            "scenario_name",
            "scenario_description",
            "access_metric",
            "county_fips",
            "county_name",
            "baseline_shock_score",
            "sensitivity_shock_score",
            "score_delta_from_baseline",
            "baseline_alert_level",
            "sensitivity_alert_level",
            "baseline_rank",
            "sensitivity_rank",
            "rank_delta_from_baseline",
            "mean_weight",
            "p90_weight",
            "threshold_weight",
            "poverty_weight",
            "rurality_weight",
            "risk_weight",
            "vulnerability_floor",
            "vulnerability_multiplier",
        ]
    ].sort_values(
        ["scenario_id", "sensitivity_rank", "county_name"],
        ascending=[True, True, True],
    )


def _prepare_county_shocks(county_shocks: pd.DataFrame) -> pd.DataFrame:
    require_columns(county_shocks, IDENTIFIER_COLUMNS, "county shocks")
    result = county_shocks.copy()
    result["county_fips"] = result["county_fips"].astype(str).str.zfill(5)
    result["county_name"] = result["county_name"].astype(str)
    result["shock_score"] = pd.to_numeric(result["shock_score"], errors="raise")
    if not VULNERABILITY_COMPONENT_COLUMNS.issubset(result.columns):
        _add_vulnerability_components(result)
    require_columns(result, VULNERABILITY_COMPONENT_COLUMNS, "county shocks")
    for column in VULNERABILITY_COMPONENT_COLUMNS | {"shock_threshold_component"}:
        result[column] = pd.to_numeric(result[column], errors="raise").clip(0, 1)
    return result


def _add_vulnerability_components(frame: pd.DataFrame) -> None:
    require_columns(
        frame,
        {"poverty_pct", "rurality_index", "high_risk_index"},
        "county shocks",
    )
    frame["vulnerability_poverty_component"] = (
        pd.to_numeric(frame["poverty_pct"], errors="raise").div(30).clip(0, 1)
    )
    frame["vulnerability_rurality_component"] = pd.to_numeric(
        frame["rurality_index"], errors="raise"
    ).clip(0, 1)
    frame["vulnerability_risk_component"] = pd.to_numeric(
        frame["high_risk_index"], errors="raise"
    ).clip(0, 1)


def _detect_access_metric(frame: pd.DataFrame) -> tuple[AccessMetric, str, str]:
    if {"shock_mean_distance_component", "shock_p90_distance_component"}.issubset(
        frame.columns
    ):
        return "distance_miles", "shock_mean_distance_component", "shock_p90_distance_component"
    if {"shock_mean_travel_time_component", "shock_p90_travel_time_component"}.issubset(
        frame.columns
    ):
        return (
            "travel_time_minutes",
            "shock_mean_travel_time_component",
            "shock_p90_travel_time_component",
        )
    raise ValueError(
        "county shocks must contain either distance or travel-time shock component columns"
    )


def _score_scenario(
    frame: pd.DataFrame,
    scenario: WeightScenario,
    mean_column: str,
    p90_column: str,
) -> pd.Series:
    mean_component = pd.to_numeric(frame[mean_column], errors="raise").clip(0, 1)
    p90_component = pd.to_numeric(frame[p90_column], errors="raise").clip(0, 1)
    threshold_component = pd.to_numeric(
        frame["shock_threshold_component"], errors="raise"
    ).clip(0, 1)
    deterioration = (
        scenario.mean_weight * mean_component
        + scenario.p90_weight * p90_component
        + scenario.threshold_weight * threshold_component
    )
    vulnerability = (
        scenario.poverty_weight * frame["vulnerability_poverty_component"]
        + scenario.rurality_weight * frame["vulnerability_rurality_component"]
        + scenario.risk_weight * frame["vulnerability_risk_component"]
    )
    score = 100 * deterioration * (
        scenario.vulnerability_floor + scenario.vulnerability_multiplier * vulnerability
    )
    return score.clip(0, 100).round(1)


def _baseline_ranks(frame: pd.DataFrame) -> pd.DataFrame:
    ranked = frame[["county_fips", "county_name", "shock_score"]].copy()
    ranked = ranked.sort_values(
        ["shock_score", "county_name"],
        ascending=[False, True],
    ).reset_index(drop=True)
    ranked["baseline_rank"] = ranked.index + 1
    return frame[["county_fips"]].merge(
        ranked[["county_fips", "baseline_rank"]],
        on="county_fips",
        how="left",
    )


def _scenario_ranks(scored: pd.DataFrame) -> pd.Series:
    ranked = scored[["county_fips", "county_name", "sensitivity_shock_score"]].copy()
    ranked = ranked.sort_values(
        ["sensitivity_shock_score", "county_name"],
        ascending=[False, True],
    ).reset_index(drop=True)
    ranked["sensitivity_rank"] = ranked.index + 1
    return scored[["county_fips"]].merge(
        ranked[["county_fips", "sensitivity_rank"]],
        on="county_fips",
        how="left",
    )["sensitivity_rank"]


def _alert_levels(scores: pd.Series) -> pd.Series:
    return pd.cut(
        scores,
        bins=[-0.001, 5, 20, 40, 100],
        labels=["NONE", "WATCH", "WARNING", "CRITICAL"],
        include_lowest=True,
    ).astype(str)


def _validate_weight_sum(value: float, label: str) -> None:
    if abs(value - 1.0) > 1e-9:
        raise ValueError(f"{label} must sum to 1.0")
