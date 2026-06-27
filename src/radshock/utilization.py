from __future__ import annotations

import pandas as pd

from radshock.schemas import UTILIZATION_COLUMNS, require_columns


def prepare_utilization(frame: pd.DataFrame) -> pd.DataFrame:
    require_columns(frame, UTILIZATION_COLUMNS, "utilization")
    result = frame.copy()
    result["county_fips"] = result["county_fips"].astype(str).str.zfill(5)
    result["period"] = result["period"].astype(str)
    result["screening_services"] = pd.to_numeric(result["screening_services"], errors="raise")
    result["eligible_beneficiaries"] = pd.to_numeric(
        result["eligible_beneficiaries"], errors="raise"
    )
    denominator = result["eligible_beneficiaries"].replace(0, pd.NA)
    result["rate_per_1000"] = 1000 * result["screening_services"] / denominator
    return result.sort_values(["county_fips", "period"]).reset_index(drop=True)


def summarize_utilization_change(
    utilization: pd.DataFrame,
    before_period: str,
    after_period: str,
) -> pd.DataFrame:
    prepared = prepare_utilization(utilization)
    before = prepared[prepared["period"] == before_period][["county_fips", "rate_per_1000"]].rename(
        columns={"rate_per_1000": "rate_per_1000_before"}
    )
    after = prepared[prepared["period"] == after_period][["county_fips", "rate_per_1000"]].rename(
        columns={"rate_per_1000": "rate_per_1000_after"}
    )
    merged = before.merge(after, on="county_fips", how="outer")
    merged["utilization_delta_per_1000"] = (
        merged["rate_per_1000_after"] - merged["rate_per_1000_before"]
    )
    merged["utilization_pct_change"] = (
        merged["utilization_delta_per_1000"] / merged["rate_per_1000_before"]
    )
    return merged.sort_values("utilization_delta_per_1000").reset_index(drop=True)
