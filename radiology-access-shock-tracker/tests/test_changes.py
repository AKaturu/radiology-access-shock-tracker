import pandas as pd

from radshock.changes import detect_changes

COLUMNS = [
    "facility_id",
    "facility_name",
    "latitude",
    "longitude",
    "annual_capacity",
    "active",
]


def test_detects_open_close_relocation_and_capacity_drop() -> None:
    before = pd.DataFrame(
        [
            ["A", "Alpha", 35.0, -78.0, 100, True],
            ["B", "Beta", 35.2, -78.2, 100, True],
        ],
        columns=COLUMNS,
    )
    after = pd.DataFrame(
        [
            ["A", "Alpha", 35.1, -78.0, 50, True],
            ["C", "Gamma", 35.3, -78.3, 100, True],
        ],
        columns=COLUMNS,
    )
    event_types = set(detect_changes(before, after)["event_type"])
    assert {"OPENED", "CLOSED", "RELOCATED", "SERVICE_REDUCTION"} <= event_types
