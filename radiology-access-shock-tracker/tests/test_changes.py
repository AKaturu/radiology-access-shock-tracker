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
    events = detect_changes(before, after)
    event_types = set(events["event_type"])
    assert {"NEW_LISTING", "POSSIBLE_CLOSURE", "RELOCATED", "SERVICE_REDUCTION"} <= event_types
    possible_closure = events.loc[events["event_type"] == "POSSIBLE_CLOSURE"].iloc[0]
    assert possible_closure["requires_verification"]
    assert "not a confirmed closure" in possible_closure["details"]


def test_missing_capacity_does_not_create_service_reduction() -> None:
    before = pd.DataFrame(
        [["A", "Alpha", 35.0, -78.0, True]],
        columns=["facility_id", "facility_name", "latitude", "longitude", "active"],
    )
    after = pd.DataFrame(
        [["A", "Alpha", 35.0, -78.0, True]],
        columns=["facility_id", "facility_name", "latitude", "longitude", "active"],
    )
    events = detect_changes(before, after)
    assert "SERVICE_REDUCTION" not in set(events["event_type"])
