from __future__ import annotations

import json
import re
import shutil
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

from radshock.snapshots import file_sha256


def archive_local_source(
    input_path: Path,
    destination_dir: Path,
    source_name: str,
    source_url: str | None = None,
    retrieved_on: date | None = None,
    force: bool = False,
) -> Path:
    """Archive a local source file with checksum and retrieval metadata."""
    if not input_path.exists():
        raise FileNotFoundError(input_path)
    retrieval_date = retrieved_on or date.today()
    destination = _source_destination(destination_dir, source_name, retrieval_date, input_path.name)
    _ensure_destination(destination, force)
    shutil.copy2(input_path, destination)
    _write_metadata(
        destination,
        source_name=source_name,
        source_url=source_url,
        retrieval_date=retrieval_date,
        retrieval_method="local-archive",
        original_filename=input_path.name,
    )
    return destination


def fetch_url_source(
    url: str,
    destination_dir: Path,
    source_name: str,
    timeout: int = 60,
    retrieved_on: date | None = None,
    force: bool = False,
) -> Path:
    """Download and archive a source file with checksum and retrieval metadata."""
    retrieval_date = retrieved_on or date.today()
    filename = _filename_from_url(url)
    destination = _source_destination(destination_dir, source_name, retrieval_date, filename)
    _ensure_destination(destination, force)
    response = requests.get(url, timeout=timeout, stream=True)
    response.raise_for_status()
    with destination.open("wb") as handle:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                handle.write(chunk)
    _write_metadata(
        destination,
        source_name=source_name,
        source_url=url,
        retrieval_date=retrieval_date,
        retrieval_method="url-download",
        original_filename=filename,
    )
    return destination


def _source_destination(
    destination_dir: Path,
    source_name: str,
    retrieval_date: date,
    filename: str,
) -> Path:
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", source_name.strip()).strip("-").lower()
    if not safe_name:
        raise ValueError("source_name must contain at least one alphanumeric character")
    safe_filename = Path(filename).name
    return destination_dir / safe_name / retrieval_date.isoformat() / safe_filename


def _ensure_destination(destination: Path, force: bool) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not force:
        raise FileExistsError(
            f"source archive already exists: {destination}. Pass force=True to overwrite."
        )


def _write_metadata(
    archived_path: Path,
    source_name: str,
    source_url: str | None,
    retrieval_date: date,
    retrieval_method: str,
    original_filename: str,
) -> None:
    metadata = {
        "source_name": source_name,
        "source_url": source_url,
        "retrieval_date": retrieval_date.isoformat(),
        "retrieval_method": retrieval_method,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "original_filename": original_filename,
        "archived_filename": archived_path.name,
        "size_bytes": archived_path.stat().st_size,
        "sha256": file_sha256(archived_path),
    }
    metadata_path = archived_path.with_suffix(archived_path.suffix + ".metadata.json")
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def _filename_from_url(url: str) -> str:
    path = unquote(urlparse(url).path)
    name = Path(path).name
    if not name:
        raise ValueError(f"could not infer filename from URL: {url}")
    return name
