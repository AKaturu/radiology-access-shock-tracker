import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from radshock.readiness import run_readiness_audit
from radshock.snapshots import file_sha256


def test_readiness_audit_blocks_synthetic_unverified_analysis(tmp_path: Path) -> None:
    analysis = tmp_path / "demo" / "analysis"
    analysis.mkdir(parents=True)
    (analysis.parent / "manifest.json").write_text('{"synthetic_data": true}\n')
    _events(analysis / "facility_events.csv", requires_verification=True)
    _county_shocks(analysis / "county_shocks.csv")
    _interventions(analysis / "intervention_rankings.csv")
    _sensitivity(analysis / "sensitivity_analysis.csv")
    audit = run_readiness_audit(analysis)
    check_statuses = {check.check_id: check.status for check in audit.checks}
    assert audit.overall_status == "BLOCKED"
    assert check_statuses["manifest"] == "BLOCKER"
    assert check_statuses["facility_events"] == "BLOCKER"


def test_readiness_audit_passes_verified_real_package(tmp_path: Path) -> None:
    package = tmp_path / "package"
    analysis = package / "analysis"
    briefs = package / "briefs"
    analysis.mkdir(parents=True)
    briefs.mkdir()
    (package / "manifest.json").write_text('{"synthetic_data": false}\n')
    _events(analysis / "facility_events.csv", requires_verification=False)
    _county_shocks(analysis / "county_shocks.csv")
    _interventions(analysis / "intervention_rankings.csv")
    _sensitivity(analysis / "sensitivity_analysis.csv")
    (briefs / "policy_brief.md").write_text("# Brief\n")
    before = _snapshot_dir(tmp_path / "snapshots" / "before")
    after = _snapshot_dir(tmp_path / "snapshots" / "after")
    source_metadata = tmp_path / "source.metadata.json"
    source_metadata.write_text(
        json.dumps(
            {
                "source_name": "reviewed-source",
                "retrieval_date": "2026-06-19",
                "retrieval_method": "local-archive",
                "sha256": "abc123",
            }
        )
        + "\n"
    )
    audit = run_readiness_audit(
        analysis,
        before_snapshot_dir=before,
        after_snapshot_dir=after,
        raw_source_metadata=source_metadata,
    )
    assert audit.overall_status == "WARN"
    warnings = {check.check_id for check in audit.checks if check.status == "WARN"}
    assert warnings == {"travel_time"}
    assert not any(check.status == "BLOCKER" for check in audit.checks)


def _events(path: Path, requires_verification: bool) -> None:
    pd.DataFrame(
        [
            {
                "facility_id": "F1",
                "facility_name": "Facility",
                "event_type": "POSSIBLE_CLOSURE",
                "severity": 1.0,
                "details": "ID absent from later snapshot; not a confirmed closure",
                "requires_verification": requires_verification,
            }
        ]
    ).to_csv(path, index=False)


def _county_shocks(path: Path) -> None:
    pd.DataFrame(
        [
            {
                "county_fips": "37001",
                "county_name": "Demo",
                "shock_score": 24.4,
                "alert_level": "WARNING",
                "shock_mean_distance_component": 0.5,
                "shock_p90_distance_component": 0.2,
                "shock_threshold_component": 0.1,
                "vulnerability_poverty_component": 0.2,
                "vulnerability_rurality_component": 0.4,
                "vulnerability_risk_component": 0.3,
            }
        ]
    ).to_csv(path, index=False)


def _interventions(path: Path) -> None:
    pd.DataFrame(
        [{"candidate_id": "C1", "candidate_name": "Candidate", "intervention_score": 90.0}]
    ).to_csv(path, index=False)


def _sensitivity(path: Path) -> None:
    pd.DataFrame(
        [
            {"scenario_id": "baseline", "county_fips": "37001"},
            {"scenario_id": "threshold_heavy", "county_fips": "37001"},
        ]
    ).to_csv(path, index=False)


def _snapshot_dir(path: Path) -> Path:
    path.mkdir(parents=True)
    facilities = path / "facilities.csv"
    pd.DataFrame(
        [["F1", "Facility", 35.0, -78.0, 1000, True]],
        columns=[
            "facility_id",
            "facility_name",
            "latitude",
            "longitude",
            "annual_capacity",
            "active",
        ],
    ).to_csv(facilities, index=False)
    metadata = {
        "as_of": "2026-06-19",
        "source_name": "reviewed-source",
        "source_url": "https://example.test/source.csv",
        "raw_source_sha256": "abc123",
        "record_count": 1,
        "active_record_count": 1,
        "sha256": file_sha256(facilities),
        "created_at_utc": datetime.now(UTC).isoformat(),
    }
    (path / "metadata.json").write_text(json.dumps(metadata) + "\n")
    return path
