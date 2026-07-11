from __future__ import annotations

from pathlib import Path

import pandas as pd

from radshock.states import resolve_state_scope

CDC_ATSDR_SVI_DOWNLOAD_PAGE = (
    "https://www.atsdr.cdc.gov/place-health/php/svi/svi-data-documentation-download.html"
)
CDC_ATSDR_SVI_2022_US_COUNTY_CSV_URL = (
    "https://svi.cdc.gov/Documents/Data/2022/csv/states_counties/SVI_2022_US_county.csv"
)

SVI_COUNTY_COLUMNS = {
    "ST_ABBR": "state",
    "FIPS": "county_fips",
    "COUNTY": "county_name",
    "LOCATION": "location",
    "E_TOTPOP": "total_population",
    "EP_POV150": "poverty_150_pct",
    "E_NOVEH": "households_no_vehicle",
    "EP_NOVEH": "households_no_vehicle_pct",
    "E_NOINT": "households_no_internet",
    "EP_NOINT": "households_no_internet_pct",
    "RPL_THEME1": "svi_socioeconomic_percentile",
    "RPL_THEME2": "svi_household_characteristics_percentile",
    "RPL_THEME3": "svi_racial_ethnic_minority_percentile",
    "RPL_THEME4": "svi_housing_transportation_percentile",
    "RPL_THEMES": "svi_overall_percentile",
}


def read_svi_county_context(path: str | Path, *, state: str = "ALL") -> pd.DataFrame:
    """Read and normalize CDC/ATSDR SVI county context for a 51-jurisdiction scope."""
    scope = resolve_state_scope(state)
    frame = pd.read_csv(path, dtype={"ST": str, "STCNTY": str, "FIPS": str})
    missing = set(SVI_COUNTY_COLUMNS).difference(frame.columns)
    if missing:
        missing_columns = ", ".join(sorted(missing))
        raise ValueError(f"CDC/ATSDR SVI county CSV missing required columns: {missing_columns}")

    result = frame[list(SVI_COUNTY_COLUMNS)].rename(columns=SVI_COUNTY_COLUMNS).copy()
    result["state"] = result["state"].astype(str).str.upper()
    result = result[result["state"].isin(scope.states)].copy()
    result["county_fips"] = result["county_fips"].astype(str).str.zfill(5)

    label_columns = {"state", "county_fips", "county_name", "location"}
    numeric_columns = [column for column in result.columns if column not in label_columns]
    for column in numeric_columns:
        result[column] = _clean_svi_numeric(result[column])

    return result.sort_values("county_fips").reset_index(drop=True)


def _clean_svi_numeric(series: pd.Series) -> pd.Series:
    result = pd.to_numeric(series, errors="coerce")
    return result.mask(result <= -900)
