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


def test_prepare_mqsa_review_command(tmp_path: Path) -> None:
    source = tmp_path / "public.txt"
    source.write_text(
        f"{'Demo Facility':<75}"
        f"{'100 Main St':<50}"
        f"{'':<50}"
        f"{'':<50}"
        f"{'Raleigh':<50}"
        f"{'NC':<2}"
        f"{'27601':<15}"
        f"{'919-555-0100':<50}"
        f"{'':<50}"
        "\n"
    )
    output = tmp_path / "review.csv"
    result = CliRunner().invoke(
        app,
        ["prepare-mqsa-review", str(source), "--output-csv", str(output), "--state", "NC"],
    )
    assert result.exit_code == 0
    review = pd.read_csv(output, dtype=str).fillna("")
    assert review.loc[0, "source_facility_name"] == "Demo Facility"
    assert review.loc[0, "facility_id"] == ""
    assert review.loc[0, "active"] == ""


def test_finalize_mqsa_review_command_writes_snapshot_ready_csv(tmp_path: Path) -> None:
    review = tmp_path / "review.csv"
    output = tmp_path / "snapshot_ready.csv"
    pd.DataFrame(
        [
            {
                "facility_id": "MQSA-NC-0001",
                "facility_name": "Demo Facility",
                "latitude": "35.7796",
                "longitude": "-78.6382",
                "annual_capacity": "1000",
                "active": "true",
                "review_status": "reviewed",
                "source_record_hash": "abc123",
                "source_name": "fda-mqsa-public",
                "source_schema_version": "fda_mqsa_pipe_delimited",
            }
        ]
    ).to_csv(review, index=False)
    result = CliRunner().invoke(
        app,
        ["finalize-mqsa-review", str(review), "--output-csv", str(output)],
    )
    assert result.exit_code == 0
    snapshot_ready = pd.read_csv(output, dtype=str)
    assert snapshot_ready.loc[0, "facility_id"] == "MQSA-NC-0001"
