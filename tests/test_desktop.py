from __future__ import annotations

from pathlib import Path

from radshock.desktop import _assert_required_outputs


def test_desktop_payload_contains_required_outputs() -> None:
    project_root = Path(__file__).resolve().parents[1]

    _assert_required_outputs(project_root / "desktop_payload" / "analysis")
