from __future__ import annotations

import numpy as np
import pandas as pd

from radshock.geo import haversine_miles
from radshock.schemas import (
    validate_counties,
    validate_facilities,
    validate_population_points,
)


def nearest_access(population_points: pd.DataFrame, facilities: pd.DataFrame) -> pd.DataFrame:
    points = validate_population_points(population_points)
    active = validate_facilities(facilities)
    active = active[active["active"]].reset_index(drop=True)
    if active.empty:
        result = points.copy()
        result["nearest_facility_id"] = pd.NA
        result["distance_miles"] = np.inf
        return result

    point_lat = points["latitude"].to_numpy()[:, None]
    point_lon = points["longitude"].to_numpy()[:, None]
    facility_lat = active["latitude"].to_numpy()[None, :]
    facility_lon = active["longitude"].to_numpy()[None, :]
    distances = haversine_miles(point_lat, point_lon, facility_lat, facility_lon)
    nearest_index = np.argmin(distances, axis=1)
    result = points.copy()
    result["nearest_facility_id"] = active.iloc[nearest_index]["facility_id"].to_numpy()
    result["distance_miles"] = distances[np.arange(len(points)), nearest_index]
    return result


def weighted_quantile(values: np.ndarray, weights: np.ndarray, quantile: float) -> float:
    if len(values) == 0 or weights.sum() <= 0:
        return float("nan")
    order = np.argsort(values)
    sorted_values = values[order]
    sorted_weights = weights[order]
    cumulative = np.cumsum(sorted_weights) / sorted_weights.sum()
    return float(np.interp(quantile, cumulative, sorted_values))


def summarize_county_access(
    population_points: pd.DataFrame,
    facilities: pd.DataFrame,
    threshold_miles: float = 30.0,
) -> pd.DataFrame:
    access = nearest_access(population_points, facilities)
    rows: list[dict[str, float | str]] = []
    for county_fips, group in access.groupby("county_fips", sort=True):
        distances = group["distance_miles"].to_numpy(dtype=float)
        weights = group["weight"].to_numpy(dtype=float)
        finite = np.isfinite(distances)
        if finite.any() and weights[finite].sum() > 0:
            mean_distance = float(np.average(distances[finite], weights=weights[finite]))
            p90_distance = weighted_quantile(distances[finite], weights[finite], 0.90)
            over = float(weights[(distances > threshold_miles) | ~finite].sum() / weights.sum())
        else:
            mean_distance = float("inf")
            p90_distance = float("inf")
            over = 1.0
        rows.append(
            {
                "county_fips": county_fips,
                "population_weight": float(weights.sum()),
                "mean_distance_miles": mean_distance,
                "p90_distance_miles": p90_distance,
                f"pct_over_{int(threshold_miles)}_miles": over,
            }
        )
    return pd.DataFrame(rows)


def compare_county_access(
    population_points: pd.DataFrame,
    before_facilities: pd.DataFrame,
    after_facilities: pd.DataFrame,
    counties: pd.DataFrame,
    threshold_miles: float = 30.0,
) -> pd.DataFrame:
    before = summarize_county_access(population_points, before_facilities, threshold_miles)
    after = summarize_county_access(population_points, after_facilities, threshold_miles)
    context = validate_counties(counties)
    threshold_column = f"pct_over_{int(threshold_miles)}_miles"
    merged = before.merge(after, on="county_fips", suffixes=("_before", "_after"))
    merged = context.merge(merged, on="county_fips", how="left")
    merged["mean_distance_delta"] = (
        merged["mean_distance_miles_after"] - merged["mean_distance_miles_before"]
    )
    merged["p90_distance_delta"] = (
        merged["p90_distance_miles_after"] - merged["p90_distance_miles_before"]
    )
    merged["pct_over_threshold_delta"] = (
        merged[f"{threshold_column}_after"] - merged[f"{threshold_column}_before"]
    )
    merged["shock_score"] = _shock_score(merged)
    merged["alert_level"] = pd.cut(
        merged["shock_score"],
        bins=[-0.001, 5, 20, 40, 100],
        labels=["NONE", "WATCH", "WARNING", "CRITICAL"],
        include_lowest=True,
    ).astype(str)
    return merged.sort_values(["shock_score", "county_name"], ascending=[False, True]).reset_index(
        drop=True
    )


def _shock_score(frame: pd.DataFrame) -> pd.Series:
    mean_component = frame["mean_distance_delta"].clip(lower=0).div(20).clip(upper=1)
    p90_component = frame["p90_distance_delta"].clip(lower=0).div(30).clip(upper=1)
    threshold_component = frame["pct_over_threshold_delta"].clip(lower=0).div(0.40).clip(upper=1)
    deterioration = 0.45 * mean_component + 0.30 * p90_component + 0.25 * threshold_component

    poverty = frame["poverty_pct"].div(30).clip(lower=0, upper=1)
    rurality = frame["rurality_index"].clip(lower=0, upper=1)
    risk = frame["high_risk_index"].clip(lower=0, upper=1)
    vulnerability = 0.4 * poverty + 0.3 * rurality + 0.3 * risk
    score = 100 * deterioration * (0.70 + 0.30 * vulnerability)
    return score.clip(lower=0, upper=100).round(1)
