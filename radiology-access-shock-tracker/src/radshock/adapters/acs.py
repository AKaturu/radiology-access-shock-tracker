from __future__ import annotations

import pandas as pd
import requests

ACS_VARIABLES = {
    "NAME": "name",
    "B17001_002E": "population_below_poverty",
    "B17001_001E": "poverty_universe",
    "B08201_002E": "households_no_vehicle",
    "B08201_001E": "households_vehicle_universe",
}


def fetch_nc_county_context(year: int = 2024, timeout: int = 30) -> pd.DataFrame:
    """Fetch selected North Carolina county indicators from the Census ACS 5-year API."""
    variables = ",".join(ACS_VARIABLES)
    url = f"https://api.census.gov/data/{year}/acs/acs5"
    response = requests.get(
        url,
        params={"get": variables, "for": "county:*", "in": "state:37"},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    frame = pd.DataFrame(payload[1:], columns=payload[0]).rename(columns=ACS_VARIABLES)
    numeric = [column for column in ACS_VARIABLES.values() if column != "name"]
    frame[numeric] = frame[numeric].apply(pd.to_numeric, errors="coerce")
    frame["county_fips"] = frame["state"] + frame["county"]
    frame["poverty_pct"] = 100 * frame["population_below_poverty"] / frame["poverty_universe"]
    frame["no_vehicle_pct"] = (
        100 * frame["households_no_vehicle"] / frame["households_vehicle_universe"]
    )
    return frame[["county_fips", "name", "poverty_pct", "no_vehicle_pct"]].sort_values(
        "county_fips"
    )
