from __future__ import annotations

import pandas as pd
import requests

PLACES_COUNTY_ENDPOINT = "https://data.cdc.gov/resource/swc5-untb.json"


def fetch_nc_mammography(timeout: int = 30) -> pd.DataFrame:
    """Fetch the current CDC PLACES county mammography measure for North Carolina."""
    params: dict[str, str | int] = {
        "$select": "year,stateabbr,locationname,locationid,measure,data_value,data_value_type",
        "$where": "stateabbr='NC' AND upper(measure) like '%MAMMOGRAM%'",
        "$limit": 5000,
    }
    response = requests.get(PLACES_COUNTY_ENDPOINT, params=params, timeout=timeout)
    response.raise_for_status()
    frame = pd.DataFrame(response.json())
    if frame.empty:
        return frame
    frame["county_fips"] = frame["locationid"].astype(str).str.zfill(5)
    frame["data_value"] = pd.to_numeric(frame["data_value"], errors="coerce")
    return frame.sort_values(["county_fips", "data_value_type"])
