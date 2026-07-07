from __future__ import annotations

import json
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd

from radshock.adapters.facilities import read_fda_mqsa_fixed_width
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


def generate_snapshot_data() -> pd.DataFrame:
    review = pd.read_csv(ALL_STATES_REVIEW, dtype=str).fillna("")
    raw = read_fda_mqsa_fixed_width(RAW_MQSA_ZIP, state=None)
    dc_raw = raw[raw["source_state"] == "DC"].copy()
    dc_review = _build_review_rows(dc_raw)
    all_rows = pd.concat([review, dc_review], ignore_index=True)
    all_rows["facility_id"] = _make_facility_id(all_rows)
    all_rows["latitude"] = pd.to_numeric(
        all_rows["latitude"].replace("", "0.0"), errors="coerce"
    ).fillna(0.0)
    all_rows["longitude"] = pd.to_numeric(
        all_rows["longitude"].replace("", "0.0"), errors="coerce"
    ).fillna(0.0)
    all_rows["annual_capacity"] = pd.to_numeric(
        all_rows.get("annual_capacity", pd.NA).replace("", pd.NA), errors="coerce"
    )
    all_rows["active"] = all_rows["active"].replace("", False).fillna(False)
    return all_rows


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


def _make_facility_id(frame: pd.DataFrame) -> list[str]:
    import hashlib
    ids = []
    for _, row in frame.iterrows():
        state = str(row.get("source_state", "")).strip()
        h = str(row.get("source_record_hash", row.get("facility_id", "")))
        if h:
            suffix = h[:12]
        else:
            suffix = hashlib.sha256(
                f"{state}-{row.get('facility_name', '')}".encode()
            ).hexdigest()[:12]
        ids.append(f"MQSA-{state}-{suffix}")
    return ids


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
