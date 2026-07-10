from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ISSUE_TEMPLATE_DIR = ROOT / ".github" / "ISSUE_TEMPLATE"


def test_evidence_gate_issue_templates_exist() -> None:
    expected_templates = {
        "expert_review.yml": [
            "Independent expert review",
            "Reviewer decision",
            "NC row-level findings",
        ],
        "data_refresh_review.yml": [
            "MQSA refresh review",
            "Source ZIP was fetched",
            "Snapshot finalization is blocked",
        ],
        "real_all_state_snapshot.yml": [
            "Real all-state MQSA snapshot intake",
            "reviewed/geocoded MQSA CSV",
            "placeholder 0/0 geocodes",
        ],
        "external_validation.yml": [
            "External validation evidence",
            "Prospective clinical validation",
            "IRB",
        ],
        "release_trust.yml": [
            "Release trust checklist",
            "SHA-256 checksum",
            "macOS code-signing and notarization",
        ],
    }

    for filename, required_phrases in expected_templates.items():
        text = (ISSUE_TEMPLATE_DIR / filename).read_text(encoding="utf-8")
        for phrase in required_phrases:
            assert phrase in text, f"{filename} is missing {phrase!r}"


def test_quarterly_mqsa_workflow_opens_refresh_issues() -> None:
    text = (ROOT / ".github" / "workflows" / "quarterly-snapshot.yml").read_text(
        encoding="utf-8"
    )

    assert "issues: write" in text
    assert "MQSA_SOURCE_CHANGED" in text
    assert "Open MQSA source-change review issue" in text
    assert "Open MQSA refresh failure issue" in text
    assert "gh issue create" in text
    assert "MQSA refresh failed" in text
