from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, cast

import pandas as pd

from radshock.schemas import require_columns

AccessMetric = Literal["distance_miles", "travel_time_minutes"]

IDENTIFIER_COLUMNS = {"county_fips", "county_name", "shock_score", "alert_level"}
VULNERABILITY_COMPONENT_COLUMNS = {
    "vulnerability_poverty_component",
    "vulnerability_rurality_component",
    "vulnerability_risk_component",
}
SENSITIVITY_REPORT_COLUMNS = {
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


def render_sensitivity_markdown(
    sensitivity: pd.DataFrame,
    *,
    title: str = "Sensitivity Analysis Review",
    top_n: int = 10,
) -> str:
    """Render a reviewer-facing Markdown summary of sensitivity-analysis outputs."""
    require_columns(sensitivity, SENSITIVITY_REPORT_COLUMNS, "sensitivity analysis")
    if top_n < 1:
        raise ValueError("top_n must be at least 1")
    frame = sensitivity.copy()
    frame["county_fips"] = frame["county_fips"].astype(str).str.zfill(5)
    for column in [
        "baseline_shock_score",
        "sensitivity_shock_score",
        "score_delta_from_baseline",
        "baseline_rank",
        "sensitivity_rank",
        "rank_delta_from_baseline",
    ]:
        frame[column] = pd.to_numeric(frame[column], errors="raise")

    if frame.empty:
        return "\n".join(
            [
                f"# {title}",
                "",
                "No sensitivity-analysis rows were available for review.",
                "",
            ]
        )

    frame["alert_changed"] = (
        frame["baseline_alert_level"].astype(str)
        != frame["sensitivity_alert_level"].astype(str)
    )
    scenario_count = int(frame["scenario_id"].nunique())
    county_count = int(frame["county_fips"].nunique())
    access_metrics = ", ".join(sorted(frame["access_metric"].astype(str).unique()))
    max_score_delta = float(frame["score_delta_from_baseline"].abs().max())
    max_rank_delta = int(frame["rank_delta_from_baseline"].abs().max())
    alert_change_count = int(frame["alert_changed"].sum())

    lines = [
        f"# {title}",
        "",
        "## Summary",
        "",
        f"- Scenarios evaluated: {scenario_count}",
        f"- Counties evaluated: {county_count}",
        f"- Access metric: {access_metrics}",
        f"- Largest absolute score change: {_format_float(max_score_delta)}",
        f"- Largest absolute rank shift: {max_rank_delta}",
        f"- Scenario-county alert-level changes: {alert_change_count}",
        "",
        "## Review Boundary",
        "",
        "- This report checks whether county shock rankings are stable under alternate weights.",
        "- It supports reviewer sign-off; it does not establish causal or clinical validation.",
        (
            "- Treat large rank or alert-level shifts as prompts for methods review before "
            "publication."
        ),
        "",
        "## Scenario Summary",
        "",
        _format_markdown_table(_scenario_summary_rows(frame)),
        "",
        "## Highest Impact Rows",
        "",
        _format_markdown_table(_highest_impact_rows(frame, top_n=top_n)),
        "",
        "## Reviewer Sign-Off Checklist",
        "",
        "- [ ] Scenario definitions match the intended publication question.",
        "- [ ] Top-ranked counties remain plausible after alternate weighting assumptions.",
        "- [ ] Alert-level changes have been reviewed against source and routing limitations.",
        (
            "- [ ] Any publication text describes sensitivity results as exploratory robustness "
            "checks."
        ),
        "",
    ]
    return "\n".join(lines)


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


def _scenario_summary_rows(frame: pd.DataFrame) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for _, group in frame.groupby("scenario_id", sort=False):
        scenario = group.iloc[0]
        top = group.sort_values(["sensitivity_rank", "county_name"]).iloc[0]
        rows.append(
            {
                "Scenario": str(scenario["scenario_name"]),
                "Top county": f"{top['county_name']} ({top['county_fips']})",
                "Max score delta": _format_float(
                    float(group["score_delta_from_baseline"].abs().max())
                ),
                "Max rank shift": str(int(group["rank_delta_from_baseline"].abs().max())),
                "Alert changes": str(int(group["alert_changed"].sum())),
                "Description": str(scenario["scenario_description"]),
            }
        )
    return rows


def _highest_impact_rows(frame: pd.DataFrame, *, top_n: int) -> list[dict[str, str]]:
    if (
        frame["rank_delta_from_baseline"].abs().max() == 0
        and frame["score_delta_from_baseline"].abs().max() == 0
        and not bool(frame["alert_changed"].any())
    ):
        return [
            {
                "Scenario": "All scenarios",
                "County": "No material score, rank, or alert-level movement",
                "Baseline score": "-",
                "Sensitivity score": "-",
                "Score delta": "0.0",
                "Rank delta": "0",
                "Alert change": "No change",
            }
        ]
    ranked = frame.assign(
        abs_rank_delta=frame["rank_delta_from_baseline"].abs(),
        abs_score_delta=frame["score_delta_from_baseline"].abs(),
    ).sort_values(
        ["abs_rank_delta", "abs_score_delta", "scenario_id", "county_name"],
        ascending=[False, False, True, True],
    )
    rows: list[dict[str, str]] = []
    for raw_row in ranked.head(top_n).to_dict(orient="records"):
        row = cast(dict[str, Any], raw_row)
        rows.append(
            {
                "Scenario": str(row["scenario_id"]),
                "County": f"{row['county_name']} ({row['county_fips']})",
                "Baseline score": _format_float(float(row["baseline_shock_score"])),
                "Sensitivity score": _format_float(float(row["sensitivity_shock_score"])),
                "Score delta": _format_float(float(row["score_delta_from_baseline"])),
                "Rank delta": str(int(row["rank_delta_from_baseline"])),
                "Alert change": (
                    f"{row['baseline_alert_level']} -> {row['sensitivity_alert_level']}"
                    if bool(row["alert_changed"])
                    else "No change"
                ),
            }
        )
    return rows


def _format_markdown_table(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "_No rows._"
    headers = list(rows[0])
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(_markdown_cell(row.get(header, "")) for header in headers)
            + " |"
        )
    return "\n".join(lines)


def _markdown_cell(value: str) -> str:
    return value.replace("\n", " ").replace("|", "\\|")


def _format_float(value: float) -> str:
    return f"{value:.1f}"
