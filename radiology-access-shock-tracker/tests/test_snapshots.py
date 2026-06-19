from datetime import date
from pathlib import Path

import pandas as pd

from radshock.snapshots import store_snapshot


def test_snapshot_writes_metadata(tmp_path: Path) -> None:
    input_csv = tmp_path / "input.csv"
    pd.DataFrame(
        [["F1", "Facility", 35.0, -78.0, 1000, True]],
        columns=[
            "facility_id",
            "facility_name",
            "latitude",
            "longitude",
            "annual_capacity",
            "active",
        ],
    ).to_csv(input_csv, index=False)
    destination = store_snapshot(input_csv, date(2026, 1, 1), tmp_path / "store")
    assert (destination / "facilities.csv").exists()
    assert (destination / "metadata.json").exists()
