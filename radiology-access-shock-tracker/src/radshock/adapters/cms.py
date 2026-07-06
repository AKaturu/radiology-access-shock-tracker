from __future__ import annotations

import pandas as pd

from radshock.schemas import require_columns

MAMMOGRAPHY_HCPCS_PREFIXES = ("77063", "77065", "77066", "77067", "G0202")


def summarize_mammography_claims(
    frame: pd.DataFrame,
    hcpcs_column: str,
    county_fips_column: str,
    services_column: str,
) -> pd.DataFrame:
    """Summarize a downloaded CMS provider/service extract by county.

    CMS schemas change by release; callers explicitly map source columns instead of relying on
    brittle hard-coded field names.
    """
    require_columns(
        frame,
        {hcpcs_column, county_fips_column, services_column},
        "CMS provider/service extract",
    )
    result = frame.copy()
    result[hcpcs_column] = result[hcpcs_column].astype(str)
    mask = result[hcpcs_column].str.startswith(MAMMOGRAPHY_HCPCS_PREFIXES)
    result = result[mask]
    result[county_fips_column] = result[county_fips_column].astype(str).str.zfill(5)
    result[services_column] = pd.to_numeric(result[services_column], errors="coerce").fillna(0)
    return (
        result.groupby(county_fips_column, as_index=False)[services_column]
        .sum()
        .rename(
            columns={
                county_fips_column: "county_fips",
                services_column: "screening_services",
            }
        )
    )
