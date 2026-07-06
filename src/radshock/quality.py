from __future__ import annotations

import pandas as pd

from radshock.schemas import require_columns, validate_facilities, validate_population_points
from radshock.travel_times import TRAVEL_TIME_REVIEW_COLUMNS


def build_data_quality_reports(
    *,
    facilities: pd.DataFrame | None = None,
    population_points: pd.DataFrame | None = None,
    mqsa_review: pd.DataFrame | None = None,
    travel_time_review: pd.DataFrame | None = None,
) -> dict[str, pd.DataFrame]:
    """Build data-quality, geocoder, identifier, and route uncertainty reports."""
    outputs: dict[str, pd.DataFrame] = {}
    quality_rows: list[dict[str, object]] = []
    if facilities is not None:
        validated = validate_facilities(facilities)
        quality_rows.extend(_facility_quality_rows(validated))
    if population_points is not None:
        points = validate_population_points(population_points)
        quality_rows.extend(_population_quality_rows(points))
    if mqsa_review is not None:
        outputs["geocoder_confidence"] = build_geocoder_confidence(mqsa_review)
        outputs["identifier_crosswalk"] = build_identifier_crosswalk(mqsa_review)
        quality_rows.extend(_mqsa_review_quality_rows(mqsa_review))
    if travel_time_review is not None:
        outputs["route_uncertainty"] = build_route_uncertainty_report(travel_time_review)
        quality_rows.extend(_route_quality_rows(travel_time_review))
    outputs["data_quality"] = pd.DataFrame(
        quality_rows,
        columns=["domain", "metric", "value", "status", "details"],
    )
    return outputs


def build_geocoder_confidence(frame: pd.DataFrame) -> pd.DataFrame:
    """Summarize row-level geocoder confidence from MQSA review provenance columns."""
    result = frame.copy().fillna("")
    for column in [
        "source_record_hash",
        "facility_id",
        "facility_name",
        "latitude",
        "longitude",
        "geocode_status",
        "geocode_provider",
        "geocode_matched_address",
        "geocode_benchmark",
        "geocode_error",
        "coordinate_quality",
    ]:
        if column not in result.columns:
            result[column] = ""
    has_coordinates = result["latitude"].astype(str).str.strip().ne("") & result[
        "longitude"
    ].astype(str).str.strip().ne("")
    status = result["geocode_status"].astype(str).str.strip().str.lower()
    coordinate_quality = result["coordinate_quality"].astype(str).str.strip().str.lower()
    result["has_coordinates"] = has_coordinates
    result["geocoder_confidence"] = "unreviewed"
    result.loc[status.eq("matched") & has_coordinates, "geocoder_confidence"] = "candidate_match"
    high_confidence = (
        status.eq("matched")
        & has_coordinates
        & coordinate_quality.isin({"reviewed", "exact", "pointaddress"})
    )
    result.loc[high_confidence, "geocoder_confidence"] = "reviewed_high"
    result.loc[
        coordinate_quality.str.contains("approx", case=False, na=False),
        "geocoder_confidence",
    ] = "approximate"
    result.loc[status.isin({"no_match", "error"}) | ~has_coordinates, "geocoder_confidence"] = (
        "needs_review"
    )
    return (
        result[
            [
                "source_record_hash",
                "facility_id",
                "facility_name",
                "has_coordinates",
                "geocode_status",
                "geocode_provider",
                "geocode_matched_address",
                "geocode_benchmark",
                "coordinate_quality",
                "geocoder_confidence",
                "geocode_error",
            ]
        ]
        .sort_values(["geocoder_confidence", "facility_name", "source_record_hash"])
        .reset_index(drop=True)
    )


def build_identifier_crosswalk(frame: pd.DataFrame) -> pd.DataFrame:
    """Create a source-to-stable-ID crosswalk from an MQSA review CSV."""
    result = frame.copy().fillna("")
    for column in [
        "facility_id",
        "facility_name",
        "source_record_hash",
        "source_facility_name",
        "source_address_1",
        "source_city",
        "source_state",
        "source_zip_code",
        "source_name",
        "source_schema_version",
        "review_status",
    ]:
        if column not in result.columns:
            result[column] = ""
    return (
        result[
            [
                "facility_id",
                "facility_name",
                "source_record_hash",
                "source_facility_name",
                "source_address_1",
                "source_city",
                "source_state",
                "source_zip_code",
                "source_name",
                "source_schema_version",
                "review_status",
            ]
        ]
        .sort_values(["facility_id", "source_record_hash"])
        .reset_index(drop=True)
    )


def build_route_uncertainty_report(frame: pd.DataFrame) -> pd.DataFrame:
    """Summarize route-review coverage, metadata completeness, and plausibility checks."""
    require_columns(frame, set(TRAVEL_TIME_REVIEW_COLUMNS), "travel time review")
    result = frame.copy().fillna("")
    route_status = result["route_status"].astype(str).str.strip().str.lower()
    review_status = result["review_status"].astype(str).str.strip().str.lower()
    routed = result[route_status.eq("routed")].copy()
    rows: list[dict[str, object]] = [
        _metric("routes", "route_rows", len(result), "PASS", "Total route-review rows."),
        _metric(
            "routes",
            "origin_points",
            result["point_id"].astype(str).nunique(),
            "PASS",
            "Unique population origins in the route-review file.",
        ),
        _metric(
            "routes",
            "routed_rows",
            int(route_status.eq("routed").sum()),
            "PASS",
            "Rows with route_status=routed.",
        ),
        _metric(
            "routes",
            "unreachable_rows",
            int(route_status.eq("unreachable").sum()),
            "PASS",
            "Rows marked unreachable by the reviewed provider.",
        ),
        _metric(
            "routes",
            "approved_rows",
            int(review_status.isin({"reviewed", "verified", "approved"}).sum()),
            "PASS" if review_status.isin({"reviewed", "verified", "approved"}).all() else "WARN",
            "Rows with approved review status.",
        ),
    ]
    if routed.empty:
        rows.append(_metric("routes", "routed_minutes_p90", "", "WARN", "No routed rows."))
        return pd.DataFrame(rows)
    routed["travel_time_minutes"] = pd.to_numeric(routed["travel_time_minutes"], errors="coerce")
    routed["straight_line_miles"] = pd.to_numeric(routed["straight_line_miles"], errors="coerce")
    hours = routed["travel_time_minutes"] / 60
    implied_speed = routed["straight_line_miles"] / hours.replace(0, pd.NA)
    high_speed_flags = int((implied_speed > 85).sum())
    missing_provider = int(routed["route_provider"].astype(str).str.strip().eq("").sum())
    rows.extend(
        [
            _metric(
                "routes",
                "routed_minutes_median",
                round(float(routed["travel_time_minutes"].median()), 3),
                "PASS",
                "Median routed travel time.",
            ),
            _metric(
                "routes",
                "routed_minutes_p90",
                round(float(routed["travel_time_minutes"].quantile(0.9)), 3),
                "PASS",
                "90th percentile routed travel time.",
            ),
            _metric(
                "routes",
                "high_implied_speed_flags",
                high_speed_flags,
                "WARN" if high_speed_flags else "PASS",
                "Rows with straight-line miles divided by minutes exceeding 85 mph.",
            ),
            _metric(
                "routes",
                "missing_provider_rows",
                missing_provider,
                "WARN" if missing_provider else "PASS",
                "Routed rows missing route_provider metadata.",
            ),
        ]
    )
    return pd.DataFrame(rows)


def _facility_quality_rows(frame: pd.DataFrame) -> list[dict[str, object]]:
    return [
        _metric("facilities", "facility_rows", len(frame), "PASS", "Validated facility rows."),
        _metric(
            "facilities",
            "active_facilities",
            int(frame["active"].sum()),
            "PASS",
            "Active facilities.",
        ),
        _metric(
            "facilities",
            "missing_capacity_rows",
            int(frame["annual_capacity"].isna().sum()),
            "PASS",
            "Annual capacity is optional unless reviewed source support exists.",
        ),
    ]


def _population_quality_rows(frame: pd.DataFrame) -> list[dict[str, object]]:
    return [
        _metric(
            "population",
            "population_points",
            len(frame),
            "PASS",
            "Validated population points.",
        ),
        _metric(
            "population",
            "counties",
            frame["county_fips"].nunique(),
            "PASS",
            "Counties represented.",
        ),
        _metric(
            "population",
            "total_weight",
            int(frame["weight"].sum()),
            "PASS",
            "Total population-point weight.",
        ),
    ]


def _mqsa_review_quality_rows(frame: pd.DataFrame) -> list[dict[str, object]]:
    review_status = (
        frame.get("review_status", pd.Series(dtype=str)).astype(str).str.strip().str.lower()
    )
    return [
        _metric("mqsa_review", "review_rows", len(frame), "PASS", "Rows in MQSA review file."),
        _metric(
            "mqsa_review",
            "approved_rows",
            int(review_status.isin({"reviewed", "verified", "approved"}).sum()),
            "PASS" if review_status.isin({"reviewed", "verified", "approved"}).all() else "WARN",
            "Rows approved for snapshot finalization.",
        ),
    ]


def _route_quality_rows(frame: pd.DataFrame) -> list[dict[str, object]]:
    route_report = build_route_uncertainty_report(frame)
    rows: list[dict[str, object]] = []
    for row in route_report.assign(domain="route_uncertainty").itertuples(index=False):
        rows.append(
            {
                "domain": str(row.domain),
                "metric": str(row.metric),
                "value": row.value,
                "status": str(row.status),
                "details": str(row.details),
            }
        )
    return rows


def _metric(
    domain: str,
    metric: str,
    value: object,
    status: str,
    details: str,
) -> dict[str, object]:
    return {
        "domain": domain,
        "metric": metric,
        "value": value,
        "status": status,
        "details": details,
    }
