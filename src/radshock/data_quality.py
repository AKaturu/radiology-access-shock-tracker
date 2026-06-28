from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from radshock.schemas import (
    CANDIDATE_COLUMNS,
    COUNTY_COLUMNS,
    FACILITY_REQUIRED_COLUMNS,
    POPULATION_POINT_COLUMNS,
    TRAVEL_TIME_MATRIX_COLUMNS,
)
from radshock.snapshots import file_sha256

QualityStatus = Literal["PASS", "WARN", "FAIL"]


@dataclass(frozen=True)
class DatasetProfile:
    name: str
    required_columns: set[str]
    key_columns: tuple[str, ...]
    numeric_columns: tuple[str, ...] = ()
    latitude_column: str | None = None
    longitude_column: str | None = None


DATASET_PROFILES: dict[str, DatasetProfile] = {
    "facilities": DatasetProfile(
        name="facilities",
        required_columns=FACILITY_REQUIRED_COLUMNS,
        key_columns=("facility_id",),
        numeric_columns=("latitude", "longitude", "annual_capacity"),
        latitude_column="latitude",
        longitude_column="longitude",
    ),
    "counties": DatasetProfile(
        name="counties",
        required_columns=COUNTY_COLUMNS,
        key_columns=("county_fips",),
        numeric_columns=(
            "centroid_lat",
            "centroid_lon",
            "eligible_population",
            "poverty_pct",
            "rurality_index",
            "high_risk_index",
        ),
        latitude_column="centroid_lat",
        longitude_column="centroid_lon",
    ),
    "population_points": DatasetProfile(
        name="population_points",
        required_columns=POPULATION_POINT_COLUMNS,
        key_columns=("point_id",),
        numeric_columns=("latitude", "longitude", "weight"),
        latitude_column="latitude",
        longitude_column="longitude",
    ),
    "candidates": DatasetProfile(
        name="candidates",
        required_columns=CANDIDATE_COLUMNS,
        key_columns=("candidate_id",),
        numeric_columns=("latitude", "longitude"),
        latitude_column="latitude",
        longitude_column="longitude",
    ),
    "travel_time_matrix": DatasetProfile(
        name="travel_time_matrix",
        required_columns=TRAVEL_TIME_MATRIX_COLUMNS,
        key_columns=("point_id", "facility_id"),
        numeric_columns=("travel_time_minutes",),
    ),
}


def audit_csv_quality(path: str | Path, dataset_type: str = "auto") -> dict[str, Any]:
    csv_path = Path(path)
    frame = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    profile = _resolve_profile(frame, dataset_type)
    checks = _run_checks(frame, profile)
    status = _overall_status(checks)
    return {
        "status": status,
        "dataset_type": profile.name,
        "path": str(csv_path),
        "sha256": file_sha256(csv_path),
        "row_count": int(len(frame)),
        "column_count": int(len(frame.columns)),
        "checks": checks,
    }


def render_quality_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# Data Quality Report",
        "",
        f"- Status: **{audit['status']}**",
        f"- Dataset type: `{audit['dataset_type']}`",
        f"- Rows: {audit['row_count']}",
        f"- Columns: {audit['column_count']}",
        f"- SHA-256: `{audit['sha256']}`",
        "",
        "## Checks",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in audit["checks"]:
        lines.append(f"| `{check['id']}` | {check['status']} | {check['detail']} |")
    lines.append("")
    return "\n".join(lines)


def _resolve_profile(frame: pd.DataFrame, dataset_type: str) -> DatasetProfile:
    normalized = dataset_type.strip().lower().replace("-", "_")
    if normalized != "auto":
        try:
            return DATASET_PROFILES[normalized]
        except KeyError as exc:
            options = ", ".join(["auto", *sorted(DATASET_PROFILES)])
            raise ValueError(f"dataset_type must be one of: {options}") from exc

    columns = set(frame.columns)
    scored = sorted(
        DATASET_PROFILES.values(),
        key=lambda profile: len(profile.required_columns & columns),
        reverse=True,
    )
    if not scored or len(scored[0].required_columns & columns) == 0:
        raise ValueError("could not infer dataset_type from CSV columns")
    return scored[0]


def _run_checks(frame: pd.DataFrame, profile: DatasetProfile) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    columns = set(frame.columns)
    missing_required = sorted(profile.required_columns - columns)
    checks.append(
        _check(
            "required_columns",
            "FAIL" if missing_required else "PASS",
            "missing: " + ", ".join(missing_required) if missing_required else "all present",
        )
    )
    if missing_required:
        return checks

    blank_counts = {
        column: int(frame[column].astype(str).str.strip().eq("").sum())
        for column in sorted(profile.required_columns)
    }
    blank_required = {key: value for key, value in blank_counts.items() if value > 0}
    checks.append(
        _check(
            "blank_required_values",
            "FAIL" if blank_required else "PASS",
            _format_counts(blank_required) if blank_required else "none",
        )
    )

    duplicate_count = 0
    if all(column in frame.columns for column in profile.key_columns):
        duplicate_count = int(frame.duplicated(list(profile.key_columns)).sum())
    checks.append(
        _check(
            "duplicate_keys",
            "FAIL" if duplicate_count else "PASS",
            f"{duplicate_count} duplicate rows across {', '.join(profile.key_columns)}",
        )
    )

    invalid_numeric = _invalid_numeric_counts(frame, profile.numeric_columns)
    checks.append(
        _check(
            "numeric_values",
            "FAIL" if invalid_numeric else "PASS",
            _format_counts(invalid_numeric) if invalid_numeric else "all parseable",
        )
    )

    range_failures = _coordinate_range_failures(frame, profile)
    checks.append(
        _check(
            "coordinate_ranges",
            "FAIL" if range_failures else "PASS",
            _format_counts(range_failures) if range_failures else "all coordinates in range",
        )
    )
    return checks


def _invalid_numeric_counts(frame: pd.DataFrame, columns: tuple[str, ...]) -> dict[str, int]:
    invalid: dict[str, int] = {}
    for column in columns:
        if column not in frame.columns:
            continue
        raw = frame[column].astype(str).str.strip()
        parsed = pd.to_numeric(raw, errors="coerce")
        count = int(raw.ne("").sum() - parsed.notna().sum())
        if count > 0:
            invalid[column] = count
    return invalid


def _coordinate_range_failures(frame: pd.DataFrame, profile: DatasetProfile) -> dict[str, int]:
    failures: dict[str, int] = {}
    if profile.latitude_column and profile.latitude_column in frame.columns:
        lat = pd.to_numeric(frame[profile.latitude_column], errors="coerce")
        count = int((lat.notna() & ~lat.between(-90, 90)).sum())
        if count > 0:
            failures[profile.latitude_column] = count
    if profile.longitude_column and profile.longitude_column in frame.columns:
        lon = pd.to_numeric(frame[profile.longitude_column], errors="coerce")
        count = int((lon.notna() & ~lon.between(-180, 180)).sum())
        if count > 0:
            failures[profile.longitude_column] = count
    return failures


def _check(check_id: str, status: QualityStatus, detail: str) -> dict[str, Any]:
    return {"id": check_id, "status": status, "detail": detail}


def _overall_status(checks: list[dict[str, Any]]) -> QualityStatus:
    statuses = {check["status"] for check in checks}
    if "FAIL" in statuses:
        return "FAIL"
    if "WARN" in statuses:
        return "WARN"
    return "PASS"


def _format_counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{key}: {value}" for key, value in sorted(counts.items()))
