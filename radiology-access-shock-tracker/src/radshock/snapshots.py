from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd

from radshock.schemas import validate_facilities


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def store_snapshot(
    input_csv: Path,
    as_of: date,
    store_dir: Path,
    source_name: str = "manual-import",
) -> Path:
    """Validate and version a facility snapshot with immutable metadata."""
    frame = validate_facilities(pd.read_csv(input_csv))
    destination = store_dir / as_of.isoformat()
    destination.mkdir(parents=True, exist_ok=False)
    snapshot_path = destination / "facilities.csv"
    frame.to_csv(snapshot_path, index=False)
    metadata = {
        "as_of": as_of.isoformat(),
        "source_name": source_name,
        "record_count": int(len(frame)),
        "active_record_count": int(frame["active"].sum()),
        "sha256": file_sha256(snapshot_path),
        "created_at_utc": datetime.now(UTC).isoformat(),
        "input_filename": input_csv.name,
    }
    (destination / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return destination


def copy_snapshot_tree(source_dir: Path, destination_dir: Path, force: bool = False) -> None:
    """Copy a snapshot tree without overwriting unless force is explicit."""
    if destination_dir.exists():
        if not force:
            raise FileExistsError(
                f"snapshot destination already exists: {destination_dir}. "
                "Pass force=True only for documented regeneration."
            )
        shutil.rmtree(destination_dir)
    shutil.copytree(source_dir, destination_dir)
