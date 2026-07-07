from __future__ import annotations

import json
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd

from radshock.adapters.facilities import finalize_mqsa_review, read_fda_mqsa_fixed_width
from radshock.snapshots import store_snapshot

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "snapshots"
ALL_STATES_REVIEW = (
    BASE_DIR
    / "work"
    / "all-states"
    / "2026-07-06-acs"
    / "review"
    / "fda_mqsa_all_50_review.csv"
)
RAW_MQSA_ZIP = (
    BASE_DIR
    / "work"
    / "all-states"
    / "2026-07-06-acs"
    / "raw"
    / "fda-mqsa-public"
    / "2026-07-06"
    / "public.zip"
)


def generate_snapshot_data(
    review_path: Path = ALL_STATES_REVIEW,
    raw_mqsa_zip: Path = RAW_MQSA_ZIP,
) -> pd.DataFrame:
    """Return snapshot-ready facilities only from a completed all-state MQSA review.

    This intentionally refuses to invent facility IDs, coordinates, active flags, or review
    approvals. If the all-state review CSV does not already include DC, raw DC rows are appended
    as review-template rows so the finalization step fails until those DC rows are completed.
    """
    review = pd.read_csv(review_path, dtype=str, keep_default_na=False).fillna("")
    all_rows = _with_dc_review_rows(review, raw_mqsa_zip)
    return finalize_mqsa_review(all_rows)


def _with_dc_review_rows(review: pd.DataFrame, raw_mqsa_zip: Path) -> pd.DataFrame:
    if "source_state" in review.columns:
        states = set(review["source_state"].astype(str).str.upper().str.strip())
        if "DC" in states:
            return review
    raw = read_fda_mqsa_fixed_width(raw_mqsa_zip, state=None)
    dc_raw = raw[raw["source_state"] == "DC"].copy()
    if dc_raw.empty:
        return review
    dc_review = _build_review_rows(dc_raw)
    return pd.concat([review, dc_review], ignore_index=True)


def _build_review_rows(dc_raw: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "facility_id", "facility_name", "latitude", "longitude",
        "annual_capacity", "active", "review_status", "source_record_hash",
        "source_name", "source_schema_version", "source_facility_name",
        "source_address_1", "source_address_2", "source_address_3",
        "source_city", "source_state", "source_zip_code", "source_phone",
        "source_fax", "is_mobile_name_hint",
    ]
    rows = []
    for _, row in dc_raw.iterrows():
        rows.append({
            "facility_id": "",
            "facility_name": row.get("source_facility_name", ""),
            "latitude": "",
            "longitude": "",
            "annual_capacity": "",
            "active": "",
            "review_status": "needs_review",
            "source_record_hash": row.get("source_record_hash", ""),
            "source_name": "fda-mqsa-public",
            "source_schema_version": "fda_mqsa_pipe_delimited",
            "source_facility_name": row.get("source_facility_name", ""),
            "source_address_1": row.get("source_address_1", ""),
            "source_address_2": row.get("source_address_2", ""),
            "source_address_3": row.get("source_address_3", ""),
            "source_city": row.get("source_city", ""),
            "source_state": "DC",
            "source_zip_code": row.get("source_zip_code", ""),
            "source_phone": row.get("source_phone", ""),
            "source_fax": row.get("source_fax", ""),
            "is_mobile_name_hint": bool(row.get("is_mobile_name_hint", False)),
        })
    return pd.DataFrame(rows, columns=columns)


def main() -> None:
    snapshot_date = date.today()
    as_of = snapshot_date.isoformat()
    output_dir = DATA_DIR / as_of
    if output_dir.exists():
        print(f"Snapshot directory already exists: {output_dir}")
        return

    df = generate_snapshot_data()
    print(f"Generated {len(df)} facility rows ({len(df[df['source_state']=='DC'])} DC)")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f:
        csv_path = Path(f.name)
        df.to_csv(f, index=False)

    try:
        store_snapshot(
            csv_path,
            as_of=snapshot_date,
            store_dir=DATA_DIR,
            source_name="fda-mqsa-all-states",
            raw_source_path=RAW_MQSA_ZIP,
            source_url="https://www.accessdata.fda.gov/premarket/ftparea/public.zip",
        )
        print(f"Snapshot stored at: {output_dir}")

        meta_path = output_dir / "metadata.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            print(f"  Record count: {meta['record_count']}")
            print(f"  Active count: {meta['active_record_count']}")
            print(f"  SHA-256: {meta['sha256']}")
    finally:
        csv_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
