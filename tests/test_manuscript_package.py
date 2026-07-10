from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_manuscript_draft_includes_numbered_references_and_figures() -> None:
    script = (ROOT / "scripts" / "build_manuscript_package.py").read_text(encoding="utf-8")
    draft = (ROOT / "docs" / "MANUSCRIPT_DRAFT.md").read_text(encoding="utf-8")

    assert "## References" in draft
    assert "doi:10.1001/jama.2024.5534" in draft
    assert "U.S. Food and Drug Administration. Mammography Facilities." in draft
    assert "Project OSRM. Project OSRM." in draft
    assert "[CITATION:" not in draft
    assert "Citation Placeholders" not in script
    assert "dashboard-overview.png" in script
    assert "readiness-audit.png" in script
    assert "interventions.png" in script


def test_manuscript_optional_dependencies_are_declared() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "manuscript = [" in pyproject
    assert "python-docx" in pyproject
    assert "reportlab" in pyproject
    assert "pillow" in pyproject
