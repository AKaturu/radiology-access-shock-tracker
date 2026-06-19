from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from radshock.cli import app


def _snapshot(path: Path, rows: list[list[object]]) -> None:
    pd.DataFrame(
        rows,
        columns=[
            "facility_id",
            "facility_name",
            "latitude",
            "longitude",
            "annual_capacity",
            "active",
        ],
    ).to_csv(path, index=False)


def test_validate_snapshot_command(tmp_path: Path) -> None:
    snapshot = tmp_path / "snapshot.csv"
    _snapshot(snapshot, [["F1", "Facility", 35.0, -78.0, 1000, True]])
    result = CliRunner().invoke(app, ["validate-snapshot", str(snapshot)])
    assert result.exit_code == 0
    assert "Snapshot valid: 1 records, 1 active" in result.output


def test_compare_snapshots_command_writes_possible_closure(tmp_path: Path) -> None:
    before = tmp_path / "before.csv"
    after = tmp_path / "after.csv"
    output = tmp_path / "events.csv"
    _snapshot(before, [["F1", "Facility", 35.0, -78.0, 1000, True]])
    _snapshot(after, [])
    result = CliRunner().invoke(
        app,
        [
            "compare-snapshots",
            "--before-csv",
            str(before),
            "--after-csv",
            str(after),
            "--output-csv",
            str(output),
        ],
    )
    assert result.exit_code == 0
    events = pd.read_csv(output)
    assert events.loc[0, "event_type"] == "POSSIBLE_CLOSURE"
