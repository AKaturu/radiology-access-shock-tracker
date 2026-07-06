from __future__ import annotations

import pandas as pd

from radshock.geo import haversine_miles
from radshock.schemas import validate_facilities


def detect_changes(
    before: pd.DataFrame,
    after: pd.DataFrame,
    relocation_threshold_miles: float = 1.0,
    capacity_drop_threshold: float = 0.25,
) -> pd.DataFrame:
    """Detect facility-level surveillance signals between two snapshots.

    Disappearances are deliberately labeled as possible closures because a missing identifier can
    also reflect source-publication, entity-resolution, or manual extraction changes.
    """
    old = validate_facilities(before).set_index("facility_id")
    new = validate_facilities(after).set_index("facility_id")
    rows: list[dict[str, object]] = []

    for facility_id in sorted(set(old.index) | set(new.index)):
        in_old = facility_id in old.index
        in_new = facility_id in new.index
        if in_new and not in_old:
            row = new.loc[facility_id]
            rows.append(
                _event(
                    facility_id,
                    row["facility_name"],
                    "NEW_LISTING",
                    1.0,
                    details="ID present only in later snapshot",
                    match_confidence=0.0,
                    matching_rationale="No prior record with the same facility_id.",
                )
            )
            continue
        if in_old and not in_new:
            row = old.loc[facility_id]
            rows.append(
                _event(
                    facility_id,
                    row["facility_name"],
                    "POSSIBLE_CLOSURE",
                    1.0,
                    details="ID absent from later snapshot; not a confirmed closure",
                    match_confidence=0.0,
                    matching_rationale=(
                        "A disappeared facility_id can reflect closure, identifier drift, "
                        "geocoding changes, or source-publication changes."
                    ),
                )
            )
            continue

        previous = old.loc[facility_id]
        current = new.loc[facility_id]
        if bool(previous["active"]) and not bool(current["active"]):
            rows.append(
                _event(
                    facility_id,
                    current["facility_name"],
                    "SERVICE_LOSS",
                    1.0,
                    details="Active status changed to false",
                    matching_rationale="Same facility_id appears in both snapshots.",
                )
            )
        elif not bool(previous["active"]) and bool(current["active"]):
            rows.append(
                _event(
                    facility_id,
                    current["facility_name"],
                    "REACTIVATED",
                    0.5,
                    details="Active status changed to true",
                    matching_rationale="Same facility_id appears in both snapshots.",
                )
            )

        moved = float(
            haversine_miles(
                previous["latitude"],
                previous["longitude"],
                current["latitude"],
                current["longitude"],
            )
        )
        if moved >= relocation_threshold_miles:
            rows.append(
                _event(
                    facility_id,
                    current["facility_name"],
                    "RELOCATED",
                    min(1.0, moved / 50.0),
                    details=f"Moved {moved:.1f} miles",
                    distance_miles=moved,
                    matching_rationale="Same facility_id appears in both snapshots.",
                )
            )

        old_capacity = previous["annual_capacity"]
        new_capacity = current["annual_capacity"]
        if pd.notna(old_capacity) and pd.notna(new_capacity) and float(old_capacity) > 0:
            old_capacity = float(old_capacity)
            new_capacity = float(new_capacity)
            drop_fraction = (old_capacity - new_capacity) / old_capacity
            if drop_fraction >= capacity_drop_threshold:
                rows.append(
                    _event(
                        facility_id,
                        current["facility_name"],
                        "SERVICE_REDUCTION",
                        min(1.0, drop_fraction),
                        details=f"Capacity fell {drop_fraction:.0%}",
                        capacity_change=new_capacity - old_capacity,
                        matching_rationale="Same facility_id appears in both snapshots.",
                    )
                )

        if str(previous["facility_name"]).strip() != str(current["facility_name"]).strip():
            rows.append(
                _event(
                    facility_id,
                    current["facility_name"],
                    "RENAMED",
                    0.1,
                    details=f"Previously: {previous['facility_name']}",
                    matching_rationale="Same facility_id appears in both snapshots.",
                )
            )

    columns = [
        "facility_id",
        "facility_name",
        "event_type",
        "severity",
        "details",
        "distance_miles",
        "capacity_change",
        "match_confidence",
        "matching_rationale",
        "requires_verification",
    ]
    return (
        pd.DataFrame(rows, columns=columns)
        .sort_values(["severity", "event_type", "facility_id"], ascending=[False, True, True])
        .reset_index(drop=True)
    )


def _event(
    facility_id: str,
    facility_name: object,
    event_type: str,
    severity: float,
    details: str,
    distance_miles: float | None = None,
    capacity_change: float | None = None,
    match_confidence: float = 1.0,
    matching_rationale: str = "Same facility_id appears in both snapshots.",
    requires_verification: bool = True,
) -> dict[str, object]:
    return {
        "facility_id": facility_id,
        "facility_name": str(facility_name),
        "event_type": event_type,
        "severity": round(float(severity), 4),
        "details": details,
        "distance_miles": distance_miles,
        "capacity_change": capacity_change,
        "match_confidence": round(float(match_confidence), 4),
        "matching_rationale": matching_rationale,
        "requires_verification": requires_verification,
    }
