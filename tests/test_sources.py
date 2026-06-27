import json
from datetime import date
from pathlib import Path

import pytest

from radshock.sources import archive_local_source


def test_archive_local_source_writes_metadata(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("raw data\n")
    archived = archive_local_source(
        source,
        tmp_path / "raw",
        "FDA MQSA Public",
        source_url="https://example.test/source.txt",
        retrieved_on=date(2026, 6, 19),
    )
    metadata = json.loads(archived.with_suffix(".txt.metadata.json").read_text())
    assert archived.exists()
    assert metadata["source_name"] == "FDA MQSA Public"
    assert metadata["source_url"] == "https://example.test/source.txt"
    assert metadata["retrieval_date"] == "2026-06-19"
    assert len(metadata["sha256"]) == 64


def test_archive_local_source_does_not_overwrite_without_force(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("raw data\n")
    archive_local_source(source, tmp_path / "raw", "source", retrieved_on=date(2026, 6, 19))
    with pytest.raises(FileExistsError):
        archive_local_source(source, tmp_path / "raw", "source", retrieved_on=date(2026, 6, 19))
