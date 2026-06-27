from __future__ import annotations

from io import StringIO

import pandas as pd
import requests

ACS_VARIABLES = {
    "NAME": "name",
    "B01001_001E": "total_population",
    "B01001_040E": "female_50_54",
    "B01001_041E": "female_55_59",
    "B01001_042E": "female_60_61",
    "B01001_043E": "female_62_64",
    "B01001_044E": "female_65_66",
    "B01001_045E": "female_67_69",
    "B01001_046E": "female_70_74",
    "B17001_002E": "population_below_poverty",
    "B17001_001E": "poverty_universe",
    "B08201_002E": "households_no_vehicle",
    "B08201_001E": "households_vehicle_universe",
}
FEMALE_50_74_COLUMNS = [
    "female_50_54",
    "female_55_59",
    "female_60_61",
    "female_62_64",
    "female_65_66",
    "female_67_69",
    "female_70_74",
]
NC_STATE_FIPS = "37"
NC_STATE_ABBR = "NC"
NC_COUNTY_GAZETTEER_URL_TEMPLATE = (
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
    "{year}_Gazetteer/{year}_gaz_counties_37.txt"
)
NC_TRACT_GAZETTEER_URL_TEMPLATE = (
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
    "{year}_Gazetteer/{year}_gaz_tracts_37.txt"
)


def fetch_nc_county_context(
    year: int = 2024,
    *,
    api_key: str | None = None,
    timeout: int = 30,
) -> pd.DataFrame:
    """Fetch selected North Carolina county indicators from the Census ACS 5-year API."""
    frame = _fetch_acs_context(
        year,
        geography="county:*",
        in_clause=f"state:{NC_STATE_FIPS}",
        api_key=api_key,
        timeout=timeout,
    )
    frame["county_fips"] = frame["state"] + frame["county"]
    return _add_derived_acs_indicators(frame).sort_values("county_fips").reset_index(drop=True)


def fetch_nc_tract_context(
    year: int = 2024,
    *,
    api_key: str | None = None,
    timeout: int = 30,
) -> pd.DataFrame:
    """Fetch selected North Carolina tract indicators from the Census ACS 5-year API."""
    frame = _fetch_acs_context(
        year,
        geography="tract:*",
        in_clause=f"state:{NC_STATE_FIPS} county:*",
        api_key=api_key,
        timeout=timeout,
    )
    frame["county_fips"] = frame["state"] + frame["county"]
    frame["tract_geoid"] = frame["county_fips"] + frame["tract"]
    return _add_derived_acs_indicators(frame).sort_values("tract_geoid").reset_index(drop=True)


def _fetch_acs_context(
    year: int,
    *,
    geography: str,
    in_clause: str,
    api_key: str | None,
    timeout: int,
) -> pd.DataFrame:
    variables = ",".join(ACS_VARIABLES)
    url = f"https://api.census.gov/data/{year}/acs/acs5"
    params = {"get": variables, "for": geography, "in": in_clause}
    if api_key is not None and api_key.strip():
        params["key"] = api_key.strip()
    response = requests.get(
        url,
        params=params,
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    frame = pd.DataFrame(payload[1:], columns=payload[0]).rename(columns=ACS_VARIABLES)
    numeric = [column for column in ACS_VARIABLES.values() if column != "name"]
    frame[numeric] = frame[numeric].apply(pd.to_numeric, errors="coerce")
    return frame


def _add_derived_acs_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["eligible_population"] = frame[FEMALE_50_74_COLUMNS].sum(axis=1)
    frame["poverty_pct"] = 100 * frame["population_below_poverty"] / frame["poverty_universe"]
    frame["no_vehicle_pct"] = (
        100 * frame["households_no_vehicle"] / frame["households_vehicle_universe"]
    )
    return frame


def fetch_nc_county_gazetteer(year: int = 2024, timeout: int = 30) -> pd.DataFrame:
    """Fetch NC county centroid and land-area data from the Census Gazetteer file."""
    url = NC_COUNTY_GAZETTEER_URL_TEMPLATE.format(year=year)
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    frame = pd.read_csv(StringIO(response.text), sep="\t", dtype=str)
    frame.columns = [column.strip() for column in frame.columns]
    result = frame.rename(
        columns={
            "GEOID": "county_fips",
            "NAME": "county_name",
            "ALAND_SQMI": "land_area_sqmi",
            "INTPTLAT": "centroid_lat",
            "INTPTLONG": "centroid_lon",
        }
    )
    numeric = ["land_area_sqmi", "centroid_lat", "centroid_lon"]
    result[numeric] = result[numeric].apply(pd.to_numeric, errors="raise")
    return result[["county_fips", "county_name", "land_area_sqmi", "centroid_lat", "centroid_lon"]]


def fetch_nc_tract_gazetteer(year: int = 2024, timeout: int = 30) -> pd.DataFrame:
    """Fetch NC tract centroid and land-area data from the Census Gazetteer file."""
    url = NC_TRACT_GAZETTEER_URL_TEMPLATE.format(year=year)
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    frame = pd.read_csv(StringIO(response.text), sep="\t", dtype=str)
    frame.columns = [column.strip() for column in frame.columns]
    result = frame.rename(
        columns={
            "GEOID": "tract_geoid",
            "NAME": "tract_name",
            "ALAND_SQMI": "land_area_sqmi",
            "INTPTLAT": "centroid_lat",
            "INTPTLONG": "centroid_lon",
        }
    )
    numeric = ["land_area_sqmi", "centroid_lat", "centroid_lon"]
    result[numeric] = result[numeric].apply(pd.to_numeric, errors="raise")
    result["county_fips"] = result["tract_geoid"].str.slice(0, 5)
    if "tract_name" not in result.columns:
        result["tract_name"] = ""
    return result[
        [
            "tract_geoid",
            "county_fips",
            "tract_name",
            "land_area_sqmi",
            "centroid_lat",
            "centroid_lon",
        ]
    ]


def build_nc_county_analysis_context(
    year: int = 2024,
    *,
    api_key: str | None = None,
    timeout: int = 30,
) -> pd.DataFrame:
    """Build the analysis-ready NC county context CSV from Census sources.

    `eligible_population` is ACS female population age 50-74 to align with the CDC PLACES
    mammography measure age band. `rurality_index` and `high_risk_index` are transparent Census
    proxies: rurality is the inverse min-max scaling of population density within NC counties, and
    high risk is the min-max scaling of households with no vehicle available.
    """
    acs = fetch_nc_county_context(year=year, api_key=api_key, timeout=timeout)
    gazetteer = fetch_nc_county_gazetteer(year=year, timeout=timeout)
    result = gazetteer.merge(acs, on="county_fips", how="inner")
    if len(result) != len(gazetteer):
        raise ValueError("Census ACS/Gazetteer county join did not preserve all NC counties")
    result["state"] = NC_STATE_ABBR
    result["population_density_per_sqmi"] = (
        result["total_population"] / result["land_area_sqmi"]
    )
    result["rurality_index"] = _inverse_min_max(result["population_density_per_sqmi"])
    result["high_risk_index"] = _min_max(result["no_vehicle_pct"])
    return result.sort_values("county_fips").reset_index(drop=True)


def build_nc_tract_analysis_context(
    year: int = 2024,
    *,
    api_key: str | None = None,
    timeout: int = 30,
) -> pd.DataFrame:
    """Build source-rich NC tract context for population-point generation.

    Tract points use ACS female population age 50-74 as weights and Census Gazetteer internal
    points as reproducible centroids. They are finer than county centroids but still represent
    tract-level approximations, not household-level locations.
    """
    acs = fetch_nc_tract_context(year=year, api_key=api_key, timeout=timeout)
    gazetteer = fetch_nc_tract_gazetteer(year=year, timeout=timeout)
    result = gazetteer.merge(acs, on=["tract_geoid", "county_fips"], how="inner")
    if len(result) != len(gazetteer):
        raise ValueError("Census ACS/Gazetteer tract join did not preserve all NC tracts")
    result["state"] = NC_STATE_ABBR
    result["population_density_per_sqmi"] = (
        result["total_population"] / result["land_area_sqmi"]
    )
    return result.sort_values("tract_geoid").reset_index(drop=True)


def to_analysis_counties(context: pd.DataFrame) -> pd.DataFrame:
    """Select the strict county schema expected by the access engine."""
    result = context[
        [
            "county_fips",
            "county_name",
            "state",
            "centroid_lat",
            "centroid_lon",
            "eligible_population",
            "poverty_pct",
            "rurality_index",
            "high_risk_index",
        ]
    ].copy()
    result["eligible_population"] = result["eligible_population"].round(0).astype("int64")
    for column in ["poverty_pct", "rurality_index", "high_risk_index"]:
        result[column] = result[column].round(6)
    return result


def to_county_centroid_population_points(context: pd.DataFrame) -> pd.DataFrame:
    """Build a testable county-centroid population-point file from Census county context."""
    result = pd.DataFrame(
        {
            "point_id": "county-" + context["county_fips"].astype(str),
            "county_fips": context["county_fips"].astype(str),
            "latitude": context["centroid_lat"],
            "longitude": context["centroid_lon"],
            "weight": context["eligible_population"].round(0).astype("int64"),
        }
    )
    return result.sort_values("point_id").reset_index(drop=True)


def to_tract_population_points(
    context: pd.DataFrame,
    *,
    include_zero_weight: bool = False,
) -> pd.DataFrame:
    """Build tract-centroid population points weighted by eligible population."""
    result = pd.DataFrame(
        {
            "point_id": "tract-" + context["tract_geoid"].astype(str),
            "county_fips": context["county_fips"].astype(str),
            "latitude": context["centroid_lat"],
            "longitude": context["centroid_lon"],
            "weight": context["eligible_population"].round(0).astype("int64"),
        }
    )
    if not include_zero_weight:
        result = result.loc[result["weight"] > 0].copy()
    return result.sort_values("point_id").reset_index(drop=True)


def _min_max(series: pd.Series) -> pd.Series:
    minimum = float(series.min())
    maximum = float(series.max())
    if maximum == minimum:
        return pd.Series(0.0, index=series.index)
    return ((series - minimum) / (maximum - minimum)).clip(lower=0, upper=1)


def _inverse_min_max(series: pd.Series) -> pd.Series:
    return 1 - _min_max(series)
