from __future__ import annotations

import pandas as pd
import requests

from radshock.states import resolve_state_scope

PLACES_COUNTY_ENDPOINT = "https://data.cdc.gov/resource/swc5-untb.json"
PLACES_MAMMOGRAPHY_MEASURE_ID = "MAMMOUSE"
PLACES_MAMMOGRAPHY_COLUMNS = [
    "year",
    "stateabbr",
    "locationname",
    "locationid",
    "measure",
    "data_value",
    "data_value_type",
]


def fetch_mammography(state: str = "NC", timeout: int = 30) -> pd.DataFrame:
    """Fetch the current CDC PLACES county mammography measure for a state scope."""
    scope = resolve_state_scope(state)
    where = f"measureid='{PLACES_MAMMOGRAPHY_MEASURE_ID}'"
    if not scope.is_all_50_states:
        where = f"stateabbr='{scope.states[0]}' AND {where}"
    params: dict[str, str | int] = {
        "$select": ",".join(PLACES_MAMMOGRAPHY_COLUMNS),
        "$where": where,
        "$limit": 100000,
    }
    response = requests.get(PLACES_COUNTY_ENDPOINT, params=params, timeout=timeout)
    response.raise_for_status()
    frame = pd.DataFrame(response.json())
    if frame.empty:
        return pd.DataFrame(columns=PLACES_MAMMOGRAPHY_COLUMNS + ["county_fips"])
    if scope.is_all_50_states:
        frame = frame[frame["stateabbr"].astype(str).str.upper().isin(scope.states)].copy()
    if frame.empty:
        return pd.DataFrame(columns=PLACES_MAMMOGRAPHY_COLUMNS + ["county_fips"])
    frame["county_fips"] = frame["locationid"].astype(str).str.zfill(5)
    frame["data_value"] = pd.to_numeric(frame["data_value"], errors="coerce")
    return frame.sort_values(["county_fips", "data_value_type"])


def fetch_nc_mammography(timeout: int = 30) -> pd.DataFrame:
    """Fetch the current CDC PLACES county mammography measure for North Carolina."""
    return fetch_mammography(state="NC", timeout=timeout)
