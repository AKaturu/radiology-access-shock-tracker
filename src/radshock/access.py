from __future__ import annotations

import numpy as np
import pandas as pd

from radshock.geo import haversine_miles
from radshock.schemas import (
    validate_counties,
    validate_facilities,
    validate_population_points,
    validate_travel_time_matrix,
)

DEFAULT_ACCESS_THRESHOLDS_MILES = (30.0, 45.0, 60.0)
DEFAULT_ACCESS_THRESHOLDS_MINUTES = (30.0, 45.0, 60.0)


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


def nearest_travel_time_access(
    population_points: pd.DataFrame,
    facilities: pd.DataFrame,
    travel_times: pd.DataFrame,
) -> pd.DataFrame:
    """Find nearest active facility using a reviewed point-to-facility travel-time matrix."""
    points = validate_population_points(population_points)
    active = validate_facilities(facilities)
    matrix = validate_travel_time_matrix(travel_times)
    active = active[active["active"]].reset_index(drop=True)
    result = points.copy()
    if active.empty:
        result["nearest_facility_id"] = pd.NA
        result["travel_time_minutes"] = np.inf
        return result

    eligible = matrix[
        matrix["point_id"].isin(points["point_id"])
        & matrix["facility_id"].isin(active["facility_id"])
    ].copy()
    if eligible.empty:
        result["nearest_facility_id"] = pd.NA
        result["travel_time_minutes"] = np.inf
        return result

    nearest = (
        eligible.sort_values(["point_id", "travel_time_minutes", "facility_id"])
        .drop_duplicates("point_id", keep="first")
        .rename(columns={"facility_id": "nearest_facility_id"})
    )
    result = result.merge(
        nearest[["point_id", "nearest_facility_id", "travel_time_minutes"]],
        on="point_id",
        how="left",
    )
    result["travel_time_minutes"] = result["travel_time_minutes"].fillna(np.inf)
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
        county_fips_text = str(county_fips)
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
                "county_fips": county_fips_text,
                "population_weight": float(weights.sum()),
                "mean_distance_miles": mean_distance,
                "p90_distance_miles": p90_distance,
                f"pct_over_{int(threshold_miles)}_miles": over,
            }
        )
    return pd.DataFrame(rows)


def summarize_county_travel_time_access(
    population_points: pd.DataFrame,
    facilities: pd.DataFrame,
    travel_times: pd.DataFrame,
    threshold_minutes: float = 45.0,
) -> pd.DataFrame:
    access = nearest_travel_time_access(population_points, facilities, travel_times)
    rows: list[dict[str, float | str]] = []
    for county_fips, group in access.groupby("county_fips", sort=True):
        county_fips_text = str(county_fips)
        times = group["travel_time_minutes"].to_numpy(dtype=float)
        weights = group["weight"].to_numpy(dtype=float)
        total_weight = float(weights.sum())
        finite = np.isfinite(times)
        if finite.any() and weights[finite].sum() > 0:
            mean_time = float(np.average(times[finite], weights=weights[finite]))
            p90_time = weighted_quantile(times[finite], weights[finite], 0.90)
            over = float(weights[(times > threshold_minutes) | ~finite].sum() / total_weight)
            coverage = float(weights[finite].sum() / total_weight)
        else:
            mean_time = float("inf")
            p90_time = float("inf")
            over = 1.0
            coverage = 0.0
        rows.append(
            {
                "county_fips": county_fips_text,
                "population_weight": total_weight,
                "mean_travel_time_minutes": mean_time,
                "p90_travel_time_minutes": p90_time,
                f"pct_over_{int(threshold_minutes)}_minutes": over,
                "travel_time_coverage": coverage,
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
    access_change = summarize_access_change(
        population_points,
        before_facilities,
        after_facilities,
        thresholds_miles=DEFAULT_ACCESS_THRESHOLDS_MILES,
    )
    merged = context.merge(merged, on="county_fips", how="left")
    merged = merged.merge(access_change, on="county_fips", how="left")
    merged["mean_distance_delta"] = (
        merged["mean_distance_miles_after"] - merged["mean_distance_miles_before"]
    )
    merged["p90_distance_delta"] = (
        merged["p90_distance_miles_after"] - merged["p90_distance_miles_before"]
    )
    merged["pct_over_threshold_delta"] = (
        merged[f"{threshold_column}_after"] - merged[f"{threshold_column}_before"]
    )
    merged = add_shock_components(merged)
    merged["alert_level"] = pd.cut(
        merged["shock_score"],
        bins=[-0.001, 5, 20, 40, 100],
        labels=["NONE", "WATCH", "WARNING", "CRITICAL"],
        include_lowest=True,
    ).astype(str)
    return merged.sort_values(["shock_score", "county_name"], ascending=[False, True]).reset_index(
        drop=True
    )


def compare_county_travel_time_access(
    population_points: pd.DataFrame,
    before_facilities: pd.DataFrame,
    after_facilities: pd.DataFrame,
    counties: pd.DataFrame,
    before_travel_times: pd.DataFrame,
    after_travel_times: pd.DataFrame,
    threshold_minutes: float = 45.0,
) -> pd.DataFrame:
    before = summarize_county_travel_time_access(
        population_points,
        before_facilities,
        before_travel_times,
        threshold_minutes,
    )
    after = summarize_county_travel_time_access(
        population_points,
        after_facilities,
        after_travel_times,
        threshold_minutes,
    )
    context = validate_counties(counties)
    threshold_column = f"pct_over_{int(threshold_minutes)}_minutes"
    merged = before.merge(after, on="county_fips", suffixes=("_before", "_after"))
    access_change = summarize_travel_time_access_change(
        population_points,
        before_facilities,
        after_facilities,
        before_travel_times,
        after_travel_times,
        thresholds_minutes=DEFAULT_ACCESS_THRESHOLDS_MINUTES,
    )
    merged = context.merge(merged, on="county_fips", how="left")
    merged = merged.merge(access_change, on="county_fips", how="left")
    merged["access_metric"] = "travel_time_minutes"
    merged["mean_travel_time_delta"] = (
        merged["mean_travel_time_minutes_after"] - merged["mean_travel_time_minutes_before"]
    )
    merged["p90_travel_time_delta"] = (
        merged["p90_travel_time_minutes_after"] - merged["p90_travel_time_minutes_before"]
    )
    merged["pct_over_threshold_delta"] = (
        merged[f"{threshold_column}_after"] - merged[f"{threshold_column}_before"]
    )
    merged = add_travel_time_shock_components(merged)
    merged["alert_level"] = pd.cut(
        merged["shock_score"],
        bins=[-0.001, 5, 20, 40, 100],
        labels=["NONE", "WATCH", "WARNING", "CRITICAL"],
        include_lowest=True,
    ).astype(str)
    return merged.sort_values(["shock_score", "county_name"], ascending=[False, True]).reset_index(
        drop=True
    )


def summarize_access_change(
    population_points: pd.DataFrame,
    before_facilities: pd.DataFrame,
    after_facilities: pd.DataFrame,
    thresholds_miles: tuple[float, ...] = DEFAULT_ACCESS_THRESHOLDS_MILES,
) -> pd.DataFrame:
    """Summarize point-level access changes without substituting county centroids."""
    before = nearest_access(population_points, before_facilities)[
        ["point_id", "county_fips", "weight", "nearest_facility_id", "distance_miles"]
    ].rename(
        columns={
            "nearest_facility_id": "nearest_facility_id_before",
            "distance_miles": "distance_miles_before",
        }
    )
    after = nearest_access(population_points, after_facilities)[
        ["point_id", "nearest_facility_id", "distance_miles"]
    ].rename(
        columns={
            "nearest_facility_id": "nearest_facility_id_after",
            "distance_miles": "distance_miles_after",
        }
    )
    merged = before.merge(after, on="point_id", how="inner")
    rows: list[dict[str, float | str]] = []
    for county_fips, group in merged.groupby("county_fips", sort=True):
        county_fips_text = str(county_fips)
        weights = group["weight"].to_numpy(dtype=float)
        changed = group["nearest_facility_id_before"].astype(str) != group[
            "nearest_facility_id_after"
        ].astype(str)
        row: dict[str, float | str] = {
            "county_fips": county_fips_text,
            "population_nearest_facility_changed": float(weights[changed.to_numpy()].sum()),
        }
        before_distance = group["distance_miles_before"].to_numpy(dtype=float)
        after_distance = group["distance_miles_after"].to_numpy(dtype=float)
        for threshold in thresholds_miles:
            before_over = (before_distance > threshold) | ~np.isfinite(before_distance)
            after_over = (after_distance > threshold) | ~np.isfinite(after_distance)
            newly_over = (~before_over) & after_over
            threshold_label = int(threshold)
            row[f"population_newly_over_{threshold_label}_miles"] = float(weights[newly_over].sum())
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_travel_time_access_change(
    population_points: pd.DataFrame,
    before_facilities: pd.DataFrame,
    after_facilities: pd.DataFrame,
    before_travel_times: pd.DataFrame,
    after_travel_times: pd.DataFrame,
    thresholds_minutes: tuple[float, ...] = DEFAULT_ACCESS_THRESHOLDS_MINUTES,
) -> pd.DataFrame:
    """Summarize point-level travel-time access changes from reviewed route matrices."""
    before = nearest_travel_time_access(population_points, before_facilities, before_travel_times)[
        ["point_id", "county_fips", "weight", "nearest_facility_id", "travel_time_minutes"]
    ].rename(
        columns={
            "nearest_facility_id": "nearest_facility_id_before",
            "travel_time_minutes": "travel_time_minutes_before",
        }
    )
    after = nearest_travel_time_access(population_points, after_facilities, after_travel_times)[
        ["point_id", "nearest_facility_id", "travel_time_minutes"]
    ].rename(
        columns={
            "nearest_facility_id": "nearest_facility_id_after",
            "travel_time_minutes": "travel_time_minutes_after",
        }
    )
    merged = before.merge(after, on="point_id", how="inner")
    rows: list[dict[str, float | str]] = []
    for county_fips, group in merged.groupby("county_fips", sort=True):
        county_fips_text = str(county_fips)
        weights = group["weight"].to_numpy(dtype=float)
        changed = group["nearest_facility_id_before"].astype(str) != group[
            "nearest_facility_id_after"
        ].astype(str)
        row: dict[str, float | str] = {
            "county_fips": county_fips_text,
            "population_nearest_facility_changed": float(weights[changed.to_numpy()].sum()),
        }
        before_time = group["travel_time_minutes_before"].to_numpy(dtype=float)
        after_time = group["travel_time_minutes_after"].to_numpy(dtype=float)
        for threshold in thresholds_minutes:
            before_over = (before_time > threshold) | ~np.isfinite(before_time)
            after_over = (after_time > threshold) | ~np.isfinite(after_time)
            newly_over = (~before_over) & after_over
            threshold_label = int(threshold)
            row[f"population_newly_over_{threshold_label}_minutes"] = float(
                weights[newly_over].sum()
            )
        rows.append(row)
    return pd.DataFrame(rows)


def add_shock_components(frame: pd.DataFrame) -> pd.DataFrame:
    """Attach transparent score components alongside the composite shock score."""
    result = frame.copy()
    result["shock_mean_distance_component"] = (
        result["mean_distance_delta"].clip(lower=0).div(20).clip(upper=1)
    )
    result["shock_p90_distance_component"] = (
        result["p90_distance_delta"].clip(lower=0).div(30).clip(upper=1)
    )
    result["shock_threshold_component"] = (
        result["pct_over_threshold_delta"].clip(lower=0).div(0.40).clip(upper=1)
    )
    return _add_vulnerability_adjusted_score(
        result,
        mean_component_column="shock_mean_distance_component",
        p90_component_column="shock_p90_distance_component",
    )


def add_travel_time_shock_components(frame: pd.DataFrame) -> pd.DataFrame:
    """Attach shock score components for travel-time access deltas."""
    result = frame.copy()
    result["shock_mean_travel_time_component"] = (
        result["mean_travel_time_delta"].clip(lower=0).div(20).clip(upper=1)
    )
    result["shock_p90_travel_time_component"] = (
        result["p90_travel_time_delta"].clip(lower=0).div(30).clip(upper=1)
    )
    result["shock_threshold_component"] = (
        result["pct_over_threshold_delta"].clip(lower=0).div(0.40).clip(upper=1)
    )
    return _add_vulnerability_adjusted_score(
        result,
        mean_component_column="shock_mean_travel_time_component",
        p90_component_column="shock_p90_travel_time_component",
    )


def _add_vulnerability_adjusted_score(
    result: pd.DataFrame,
    mean_component_column: str,
    p90_component_column: str,
) -> pd.DataFrame:
    result["deterioration_component"] = (
        0.45 * result[mean_component_column]
        + 0.30 * result[p90_component_column]
        + 0.25 * result["shock_threshold_component"]
    )

    result["vulnerability_poverty_component"] = result["poverty_pct"].div(30).clip(lower=0, upper=1)
    result["vulnerability_rurality_component"] = result["rurality_index"].clip(lower=0, upper=1)
    result["vulnerability_risk_component"] = result["high_risk_index"].clip(lower=0, upper=1)
    result["vulnerability_component"] = (
        0.4 * result["vulnerability_poverty_component"]
        + 0.3 * result["vulnerability_rurality_component"]
        + 0.3 * result["vulnerability_risk_component"]
    )
    score = (
        100 * result["deterioration_component"] * (0.70 + 0.30 * result["vulnerability_component"])
    )
    result["shock_score"] = score.clip(lower=0, upper=100).round(1)
    return result
