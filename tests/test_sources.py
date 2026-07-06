import json
from datetime import date
from pathlib import Path

import pytest

from radshock.sources import SOURCE_DOWNLOAD_USER_AGENT, archive_local_source, fetch_url_source


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


def test_fetch_url_source_uses_project_user_agent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[dict[str, object]] = []

    class Response:
        def raise_for_status(self) -> None:
            return None

        def iter_content(self, chunk_size: int) -> list[bytes]:
            calls.append({"chunk_size": chunk_size})
            return [b"raw data\n"]

    def fake_get(
        url: str,
        *,
        timeout: int,
        stream: bool,
        headers: dict[str, str],
    ) -> Response:
        calls.append(
            {
                "url": url,
                "timeout": timeout,
                "stream": stream,
                "headers": headers,
            }
        )
        return Response()

    monkeypatch.setattr("radshock.sources.requests.get", fake_get)

    archived = fetch_url_source(
        "https://example.test/source.zip",
        tmp_path / "raw",
        "FDA MQSA Public",
        retrieved_on=date(2026, 6, 19),
    )

    assert archived.read_bytes() == b"raw data\n"
    assert calls[0]["headers"] == {
        "Accept": "*/*",
        "User-Agent": SOURCE_DOWNLOAD_USER_AGENT,
    }
