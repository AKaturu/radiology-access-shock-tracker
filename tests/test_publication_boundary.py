from __future__ import annotations

from pathlib import Path

from radshock.publication import PUBLICATION_BOUNDARY_NOTICE

ROOT = Path(__file__).resolve().parents[1]


def test_publication_boundary_notice_separates_nc_from_all_state_claims() -> None:
    assert "NC row-level" in PUBLICATION_BOUNDARY_NOTICE
    assert "51-jurisdiction package is readiness-level only" in PUBLICATION_BOUNDARY_NOTICE
    assert "reviewed/geocoded all-state MQSA snapshot" in PUBLICATION_BOUNDARY_NOTICE
    assert "state routing matrices" in PUBLICATION_BOUNDARY_NOTICE


def test_dashboard_renders_publication_boundary_notice() -> None:
    app_source = (ROOT / "src" / "radshock" / "app.py").read_text(encoding="utf-8")

    assert "PUBLICATION_BOUNDARY_NOTICE" in app_source
    assert "st.info(PUBLICATION_BOUNDARY_NOTICE)" in app_source
