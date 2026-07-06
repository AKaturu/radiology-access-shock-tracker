from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from radshock.schemas import require_columns
from radshock.snapshots import file_sha256
from radshock.utilization import prepare_utilization


def build_causal_study_exports(
    utilization: pd.DataFrame,
    county_shocks: pd.DataFrame,
    *,
    pre_periods: list[str],
    post_periods: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build reviewer-ready descriptive pre/post utilization export tables.

    These tables are intentionally design inputs, not causal estimates. They expose period
    assignment, access-shock exposure, and county-level rate changes so a downstream statistical
    workflow can define the estimand and model explicitly.
    """
    if not pre_periods:
        raise ValueError("pre_periods must contain at least one period")
    if not post_periods:
        raise ValueError("post_periods must contain at least one period")
    overlap = sorted(set(pre_periods) & set(post_periods))
    if overlap:
        raise ValueError(f"periods cannot be both pre and post: {overlap}")

    prepared = prepare_utilization(utilization)
    require_columns(
        county_shocks,
        {"county_fips", "county_name", "shock_score", "alert_level"},
        "county shocks",
    )
    shocks = county_shocks.copy()
    shocks["county_fips"] = shocks["county_fips"].astype(str).str.zfill(5)
    shocks["shock_score"] = pd.to_numeric(shocks["shock_score"], errors="raise")

    selected_periods = set(pre_periods) | set(post_periods)
    period_panel = prepared[prepared["period"].isin(selected_periods)].copy()
    period_panel["study_phase"] = period_panel["period"].map(
        {period: "pre" for period in pre_periods} | {period: "post" for period in post_periods}
    )
    period_panel = period_panel.merge(
        shocks[["county_fips", "county_name", "shock_score", "alert_level"]],
        on="county_fips",
        how="left",
    )
    period_panel["exposure_group"] = period_panel["alert_level"].map(_exposure_group)
    period_panel = (
        period_panel[
            [
                "county_fips",
                "county_name",
                "period",
                "study_phase",
                "screening_services",
                "eligible_beneficiaries",
                "rate_per_1000",
                "shock_score",
                "alert_level",
                "exposure_group",
            ]
        ]
        .sort_values(["county_fips", "period"])
        .reset_index(drop=True)
    )

    county_summary = _county_pre_post_summary(period_panel, pre_periods, post_periods)
    return county_summary, period_panel


def write_causal_export_metadata(
    path: Path,
    *,
    utilization_csv: Path,
    county_shocks_csv: Path,
    county_export_csv: Path,
    period_export_csv: Path,
    pre_periods: list[str],
    post_periods: list[str],
    county_rows: int,
    period_rows: int,
    force: bool = False,
) -> None:
    """Write provenance for causal-study export tables."""
    if path.exists() and not force:
        raise ValueError(f"output already exists: {path}")
    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source_name": "radshock-causal-study-export",
        "claim_boundary": (
            "Exports are descriptive study-design tables. They do not estimate a causal effect."
        ),
        "periods": {
            "pre_periods": pre_periods,
            "post_periods": post_periods,
        },
        "inputs": {
            "utilization_csv": {
                "path": str(utilization_csv),
                "sha256": file_sha256(utilization_csv),
            },
            "county_shocks_csv": {
                "path": str(county_shocks_csv),
                "sha256": file_sha256(county_shocks_csv),
            },
        },
        "outputs": {
            "county_export_csv": {
                "path": str(county_export_csv),
                "sha256": file_sha256(county_export_csv),
            },
            "period_export_csv": {
                "path": str(period_export_csv),
                "sha256": file_sha256(period_export_csv),
            },
        },
        "row_counts": {
            "county_rows": county_rows,
            "period_rows": period_rows,
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _county_pre_post_summary(
    period_panel: pd.DataFrame,
    pre_periods: list[str],
    post_periods: list[str],
) -> pd.DataFrame:
    grouped = period_panel.groupby(["county_fips", "study_phase"], as_index=False).agg(
        periods_observed=("period", "nunique"),
        screening_services=("screening_services", "sum"),
        eligible_beneficiaries=("eligible_beneficiaries", "sum"),
        mean_rate_per_1000=("rate_per_1000", "mean"),
    )
    wide = grouped.pivot(index="county_fips", columns="study_phase")
    wide.columns = [
        "_".join(str(part) for part in column).strip("_")
        if isinstance(column, tuple)
        else str(column)
        for column in wide.columns
    ]
    wide = wide.reset_index()
    county_identity = (
        period_panel[["county_fips", "county_name", "shock_score", "alert_level", "exposure_group"]]
        .drop_duplicates("county_fips")
        .copy()
    )
    result = county_identity.merge(wide, on="county_fips", how="left")
    result["pre_periods"] = ",".join(pre_periods)
    result["post_periods"] = ",".join(post_periods)
    result["rate_delta_per_1000"] = (
        result["mean_rate_per_1000_post"] - result["mean_rate_per_1000_pre"]
    )
    result["rate_pct_change"] = result["rate_delta_per_1000"] / result["mean_rate_per_1000_pre"]
    for column in [
        "mean_rate_per_1000_pre",
        "mean_rate_per_1000_post",
        "rate_delta_per_1000",
        "rate_pct_change",
    ]:
        result[column] = pd.to_numeric(result[column], errors="coerce").round(6)
    return result[
        [
            "county_fips",
            "county_name",
            "alert_level",
            "exposure_group",
            "shock_score",
            "pre_periods",
            "post_periods",
            "periods_observed_pre",
            "periods_observed_post",
            "screening_services_pre",
            "screening_services_post",
            "eligible_beneficiaries_pre",
            "eligible_beneficiaries_post",
            "mean_rate_per_1000_pre",
            "mean_rate_per_1000_post",
            "rate_delta_per_1000",
            "rate_pct_change",
        ]
    ].sort_values(["exposure_group", "shock_score", "county_name"], ascending=[True, False, True])


def _exposure_group(alert_level: object) -> str:
    normalized = str(alert_level).strip().upper()
    if normalized in {"WARNING", "CRITICAL"}:
        return "higher_shock"
    if normalized == "WATCH":
        return "watch"
    return "lower_shock"
