from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pandas as pd
import pytest

SNAPSHOT_SCRIPT = (
    Path(__file__).resolve().parents[1] / "scripts" / "generate_all_state_snapshots.py"
)


def _load_snapshot_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("generate_all_state_snapshots", SNAPSHOT_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SNAPSHOT_MODULE = _load_snapshot_script()


def test_snapshot_generation_rejects_unapproved_review_rows(tmp_path: Path) -> None:
    review_path = tmp_path / "review.csv"
    pd.DataFrame([_mqsa_review_row(review_status="needs_review")]).to_csv(review_path, index=False)

    with pytest.raises(ValueError, match="not approved"):
        SNAPSHOT_MODULE.generate_snapshot_data(review_path, tmp_path / "raw.zip")


def test_snapshot_generation_accepts_reviewed_dc_rows(tmp_path: Path) -> None:
    review_path = tmp_path / "review.csv"
    pd.DataFrame([_mqsa_review_row(source_state="DC")]).to_csv(review_path, index=False)

    result = SNAPSHOT_MODULE.generate_snapshot_data(review_path, tmp_path / "raw.zip")

    assert len(result) == 1
    assert result.loc[0, "facility_id"] == "MQSA-DC-reviewed"
    assert result.loc[0, "source_state"] == "DC"
    assert bool(result.loc[0, "active"]) is True


def test_snapshot_generation_appends_unreviewed_dc_rows_until_completed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    review_path = tmp_path / "review.csv"
    pd.DataFrame([_mqsa_review_row(source_state="AL", facility_id="MQSA-AL-reviewed")]).to_csv(
        review_path, index=False
    )

    monkeypatch.setattr(
        SNAPSHOT_MODULE,
        "read_fda_mqsa_fixed_width",
        lambda *args, **kwargs: pd.DataFrame([_raw_mqsa_row()]),
    )

    with pytest.raises(ValueError, match="MQSA review is incomplete"):
        SNAPSHOT_MODULE.generate_snapshot_data(review_path, tmp_path / "raw.zip")


def _mqsa_review_row(
    *,
    source_state: str = "DC",
    facility_id: str = "MQSA-DC-reviewed",
    review_status: str = "approved",
) -> dict[str, object]:
    return {
        "facility_id": facility_id,
        "facility_name": "Reviewed Mammography Center",
        "latitude": "38.8977",
        "longitude": "-77.0365",
        "annual_capacity": "",
        "active": "true",
        "review_status": review_status,
        "source_record_hash": f"hash-{source_state.lower()}",
        "source_name": "fda-mqsa-public",
        "source_schema_version": "fda_mqsa_pipe_delimited",
        "source_facility_name": "Reviewed Mammography Center",
        "source_address_1": "1600 Pennsylvania Ave NW",
        "source_address_2": "",
        "source_address_3": "",
        "source_city": "Washington" if source_state == "DC" else "Montgomery",
        "source_state": source_state,
        "source_zip_code": "20500" if source_state == "DC" else "36104",
        "source_phone": "",
        "source_fax": "",
        "is_mobile_name_hint": False,
    }


def _raw_mqsa_row() -> dict[str, object]:
    return {
        "source_facility_name": "Unreviewed DC Mammography Center",
        "source_address_1": "1 First St NE",
        "source_address_2": "",
        "source_address_3": "",
        "source_city": "Washington",
        "source_state": "DC",
        "source_zip_code": "20002",
        "source_phone": "",
        "source_fax": "",
        "source_record_hash": "hash-unreviewed-dc",
        "is_mobile_name_hint": False,
    }
