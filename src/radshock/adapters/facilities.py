from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path

import pandas as pd

from radshock.schemas import (
    FACILITY_REQUIRED_COLUMNS,
    require_columns,
    validate_facilities,
)

FDA_MQSA_PUBLIC_ZIP_URL = "https://www.accessdata.fda.gov/premarket/ftparea/public.zip"

FDA_MQSA_FIXED_WIDTH_LAYOUT = [
    ("source_facility_name", 75),
    ("source_address_1", 50),
    ("source_address_2", 50),
    ("source_address_3", 50),
    ("source_city", 50),
    ("source_state", 2),
    ("source_zip_code", 15),
    ("source_phone", 50),
    ("source_fax", 50),
]

MQSA_REVIEW_REQUIRED_COLUMNS = FACILITY_REQUIRED_COLUMNS | {
    "review_status",
    "source_record_hash",
    "source_name",
    "source_schema_version",
}

MQSA_REVIEW_APPROVED_STATUSES = {"reviewed", "verified", "approved"}
MQSA_REVIEW_CARRY_FORWARD_COLUMNS = [
    "facility_id",
    "facility_name",
    "latitude",
    "longitude",
    "annual_capacity",
    "active",
    "review_status",
]
MQSA_REVIEW_OPTIONAL_CARRY_FORWARD_COLUMNS = {
    "review_notes",
    "coordinate_source",
    "coordinate_quality",
    "coordinate_review_notes",
}


def normalize_manual_facility_export(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize a reviewed facility export into the tracker snapshot schema.

    The FDA public search interface does not promise a stable bulk API. The MVP therefore
    requires a dated, archived export or reviewed extraction before snapshot ingestion.
    """
    aliases = {
        "id": "facility_id",
        "name": "facility_name",
        "lat": "latitude",
        "lon": "longitude",
        "capacity": "annual_capacity",
        "is_active": "active",
    }
    result = frame.rename(columns={key: value for key, value in aliases.items() if key in frame})
    missing = sorted(FACILITY_REQUIRED_COLUMNS - set(result.columns))
    if missing:
        raise ValueError(
            "manual facility export is missing required normalized columns: " + ", ".join(missing)
        )
    return validate_facilities(result)


def read_fda_mqsa_fixed_width(path: Path, state: str | None = None) -> pd.DataFrame:
    """Read the FDA MQSA public facility file from text or ZIP input.

    FDA documents a fixed-width layout, but the current public ZIP may contain pipe-delimited rows.
    This reader detects both formats and records the observed source schema.
    """
    payload = _read_text_or_zip_payload(path)
    names = [name for name, _width in FDA_MQSA_FIXED_WIDTH_LAYOUT]
    if _looks_pipe_delimited(payload):
        frame = pd.read_csv(
            io.StringIO(payload),
            sep="|",
            names=names,
            dtype=str,
            header=None,
            keep_default_na=False,
        )
        source_schema_version = "fda_mqsa_pipe_delimited"
    else:
        widths = [width for _name, width in FDA_MQSA_FIXED_WIDTH_LAYOUT]
        frame = pd.read_fwf(
            io.StringIO(payload),
            widths=widths,
            names=names,
            dtype=str,
            header=None,
        )
        source_schema_version = "fda_mqsa_fixed_width_2025_03_20"
    frame = frame.fillna("")
    for column in names:
        frame[column] = frame[column].astype(str).str.strip()
    frame = frame[(frame[names] != "").any(axis=1)].reset_index(drop=True)
    frame["source_state"] = frame["source_state"].str.upper()
    if state is not None:
        frame = frame[frame["source_state"] == state.upper()].reset_index(drop=True)
    frame["source_record_hash"] = frame.apply(_source_record_hash, axis=1)
    frame["source_name"] = "fda-mqsa-public"
    frame["source_schema_version"] = source_schema_version
    frame["is_mobile_name_hint"] = frame["source_facility_name"].str.contains(
        "mobile", case=False, na=False
    )
    return frame


def build_mqsa_review_template(raw_mqsa: pd.DataFrame) -> pd.DataFrame:
    """Build a human-review template without inventing IDs, coordinates, status, or capacity."""
    required_source_columns = {name for name, _width in FDA_MQSA_FIXED_WIDTH_LAYOUT} | {
        "source_record_hash"
    }
    missing = sorted(required_source_columns - set(raw_mqsa.columns))
    if missing:
        raise ValueError("FDA MQSA source data is missing columns: " + ", ".join(missing))
    result = raw_mqsa.copy()
    result.insert(0, "facility_id", "")
    result.insert(1, "facility_name", result["source_facility_name"])
    result.insert(2, "latitude", "")
    result.insert(3, "longitude", "")
    result.insert(4, "annual_capacity", "")
    result.insert(5, "active", "")
    result.insert(6, "review_status", "needs_review")
    ordered = [
        "facility_id",
        "facility_name",
        "latitude",
        "longitude",
        "annual_capacity",
        "active",
        "review_status",
        "source_record_hash",
        "source_name",
        "source_schema_version",
        "source_facility_name",
        "source_address_1",
        "source_address_2",
        "source_address_3",
        "source_city",
        "source_state",
        "source_zip_code",
        "source_phone",
        "source_fax",
        "is_mobile_name_hint",
    ]
    return result[ordered]


def carry_forward_mqsa_review(
    current_review: pd.DataFrame,
    previous_review: pd.DataFrame,
) -> pd.DataFrame:
    """Copy reviewed MQSA fields for rows whose source record hash is unchanged."""
    require_columns(current_review, {"source_record_hash"}, "current MQSA review")
    require_columns(previous_review, {"source_record_hash"}, "previous MQSA review")
    _require_unique_source_hashes(current_review, "current MQSA review")
    _require_unique_source_hashes(previous_review, "previous MQSA review")

    result = current_review.copy()
    for column in ["source_record_hash", "review_status"]:
        if column in result:
            result[column] = result[column].astype(str).str.strip()
    previous = previous_review.copy()
    previous["source_record_hash"] = previous["source_record_hash"].astype(str).str.strip()
    carry_columns = _mqsa_carry_forward_columns(result, previous)
    if not carry_columns:
        return result

    previous_index = previous.set_index("source_record_hash", drop=False)
    matched = result["source_record_hash"].isin(previous_index.index)
    if not matched.any():
        return result

    previous_matches = previous_index.reindex(result.loc[matched, "source_record_hash"])
    for column in carry_columns:
        if column not in result.columns:
            result[column] = ""
        result.loc[matched, column] = previous_matches[column].astype("object").to_numpy()
    return result


def finalize_mqsa_review(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate a completed MQSA review CSV and return snapshot-ready facility rows."""
    require_columns(frame, MQSA_REVIEW_REQUIRED_COLUMNS, "MQSA review")
    result = frame.copy()
    for column in MQSA_REVIEW_REQUIRED_COLUMNS:
        result[column] = result[column].astype(str).str.strip()

    _require_no_blank_review_values(result)
    status = result["review_status"].str.lower()
    invalid_status = ~status.isin(MQSA_REVIEW_APPROVED_STATUSES)
    if invalid_status.any():
        examples = result.loc[invalid_status, ["source_record_hash", "review_status"]].head(5)
        raise ValueError(
            "MQSA review contains rows that are not approved for snapshot ingestion: "
            + examples.to_dict(orient="records").__repr__()
        )

    return validate_facilities(result)


def _mqsa_carry_forward_columns(
    current_review: pd.DataFrame,
    previous_review: pd.DataFrame,
) -> list[str]:
    columns: list[str] = [
        column
        for column in MQSA_REVIEW_CARRY_FORWARD_COLUMNS
        if column in current_review.columns and column in previous_review.columns
    ]
    optional_columns = [
        column
        for column in previous_review.columns
        if (column.startswith("geocode_") or column in MQSA_REVIEW_OPTIONAL_CARRY_FORWARD_COLUMNS)
    ]
    for column in optional_columns:
        if column not in columns:
            columns.append(column)
    return columns


def _require_unique_source_hashes(frame: pd.DataFrame, label: str) -> None:
    hashes = frame["source_record_hash"].astype(str).str.strip()
    duplicates = hashes[hashes.duplicated()]
    if not duplicates.empty:
        raise ValueError(
            f"{label} contains duplicate source_record_hash values: "
            + duplicates.head(5).tolist().__repr__()
        )


def _read_text_or_zip_payload(path: Path) -> str:
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            candidates = [
                name
                for name in archive.namelist()
                if not name.endswith("/") and "__MACOSX" not in name
            ]
            if not candidates:
                raise ValueError(f"ZIP archive contains no source files: {path}")
            with archive.open(candidates[0]) as handle:
                return handle.read().decode("latin-1", errors="replace")
    return path.read_text(encoding="latin-1", errors="replace")


def _require_no_blank_review_values(frame: pd.DataFrame) -> None:
    checked_columns = sorted(FACILITY_REQUIRED_COLUMNS | {"review_status"})
    blank_messages: list[str] = []
    for column in checked_columns:
        blank = frame[column].isna() | (frame[column].astype(str).str.strip() == "")
        if blank.any():
            hashes = frame.loc[blank, "source_record_hash"].head(5).tolist()
            blank_messages.append(f"{column} blank for source_record_hash values {hashes}")
    if blank_messages:
        raise ValueError("MQSA review is incomplete: " + "; ".join(blank_messages))


def _looks_pipe_delimited(payload: str) -> bool:
    for line in payload.splitlines():
        if line.strip():
            return line.count("|") >= 8
    return False


def _source_record_hash(row: pd.Series) -> str:
    values = [str(row[name]).strip().upper() for name, _width in FDA_MQSA_FIXED_WIDTH_LAYOUT]
    return hashlib.sha256("|".join(values).encode("utf-8")).hexdigest()
