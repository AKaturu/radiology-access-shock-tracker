from __future__ import annotations

import pandas as pd

from radshock.schemas import FACILITY_COLUMNS, validate_facilities


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
    missing = sorted(FACILITY_COLUMNS - set(result.columns))
    if missing:
        raise ValueError(
            "manual facility export is missing required normalized columns: "
            + ", ".join(missing)
        )
    return validate_facilities(result)
