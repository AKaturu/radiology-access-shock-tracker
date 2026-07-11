import math

import pandas as pd

from radshock.utilization import summarize_utilization_change


def test_zero_baseline_rate_has_undefined_percentage_change() -> None:
    utilization = pd.DataFrame(
        [
            ["before", "37001", 0, 100],
            ["after", "37001", 10, 100],
        ],
        columns=[
            "period",
            "county_fips",
            "screening_services",
            "eligible_beneficiaries",
        ],
    )

    result = summarize_utilization_change(utilization, "before", "after")

    assert result.loc[0, "utilization_delta_per_1000"] == 100
    assert math.isnan(result.loc[0, "utilization_pct_change"])


def test_nonzero_baseline_rate_preserves_percentage_change() -> None:
    utilization = pd.DataFrame(
        [
            ["before", "37001", 10, 100],
            ["after", "37001", 15, 100],
        ],
        columns=[
            "period",
            "county_fips",
            "screening_services",
            "eligible_beneficiaries",
        ],
    )

    result = summarize_utilization_change(utilization, "before", "after")

    assert result.loc[0, "utilization_pct_change"] == 0.5
