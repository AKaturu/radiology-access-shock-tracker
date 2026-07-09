from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _package_sources() -> set[str]:
    script = (ROOT / "scripts" / "package_release.ps1").read_text()
    return {match.group(1) for match in re.finditer(r'@\("([^"]+)",\s*"[^"]+"\)', script)}


def test_release_package_sources_are_tracked_repo_artifacts() -> None:
    sources = _package_sources()

    assert "docs/EXPERT_REVIEW_PACKET.md" in sources
    assert "docs/MANUSCRIPT_DRAFT.md" in sources
    assert "desktop_payload/analysis/manifest.json" in sources
    assert "desktop_payload/analysis/sensitivity_review.md" in sources
    assert "data/travel_times/2026-06-20_tract_nearest20_osrm_matrix.csv" in sources
    assert not any(source.startswith("work/") for source in sources)

    missing = sorted(source for source in sources if not (ROOT / source).exists())
    assert missing == []


def test_deleted_placeholder_snapshot_directory_is_not_unignored() -> None:
    gitignore = (ROOT / ".gitignore").read_text()

    assert "data/snapshots/2026-07-06" not in gitignore


def test_release_package_check_is_required_by_ci_and_branch_protection() -> None:
    workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text()
    assert re.search(r"(?m)^  release-package:\s*$", workflow)

    for template in (
        ROOT / ".github" / "branch-protection.main.json",
        ROOT / ".github" / "branch-protection.master.json",
    ):
        protection = json.loads(template.read_text())
        contexts = protection["required_status_checks"]["contexts"]
        assert contexts == ["test", "release-package"]
