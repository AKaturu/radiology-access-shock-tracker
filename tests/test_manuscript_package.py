from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_manuscript_builder_declares_citation_placeholders_and_figures() -> None:
    script = (ROOT / "scripts" / "build_manuscript_package.py").read_text(encoding="utf-8")

    assert "[CITATION: FDA MQSA public facility file]" in script
    assert "[CITATION: OSRM/OpenStreetMap routing]" in script
    assert "dashboard-overview.png" in script
    assert "readiness-audit.png" in script
    assert "interventions.png" in script


def test_manuscript_optional_dependencies_are_declared() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "manuscript = [" in pyproject
    assert "python-docx" in pyproject
    assert "reportlab" in pyproject
    assert "pillow" in pyproject
