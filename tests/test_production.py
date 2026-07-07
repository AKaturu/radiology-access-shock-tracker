from __future__ import annotations

import json
from pathlib import Path

from radshock.production import (
    audit_all_states_manifest,
    audit_production_config,
    audit_readiness_json,
    production_overall_status,
    run_production_audit,
)


def test_audit_production_config_checks_owners_and_env(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = tmp_path / "config.toml"
    config.write_text(_config_toml(required_env='["CENSUS_API_KEY"]'), encoding="utf-8")
    monkeypatch.setenv("CENSUS_API_KEY", "test-key")

    report = audit_production_config(config)

    assert set(report["status"]) == {"PASS"}


def test_audit_production_config_blocks_missing_owner_and_secret(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text(
        _config_toml(
            required_env='["MISSING_SECRET"]',
            mqsa_snapshot_owners="[]",
        ),
        encoding="utf-8",
    )

    report = audit_production_config(config)

    blockers = report[report["status"] == "BLOCKER"]
    assert {"mqsa_snapshot", "MISSING_SECRET"} <= set(blockers["check"])


def test_all_states_manifest_warns_on_missing_acs_when_not_required(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "state_scope": "ALL_STATES",
                "publication_status": "not_ready_for_publication",
                "readiness_gates": ["review required"],
                "state_coverage": {
                    "states": 51,
                    "states_with_all_public_no_secret_sources": 51,
                    "states_with_acs_county_context": 0,
                    "states_with_acs_tract_context": 0,
                },
                "state_coverage_gaps": missing_acs_gaps(),
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report = audit_all_states_manifest(manifest, require_acs=False)
    statuses = dict(zip(report["check"], report["status"], strict=True))

    assert statuses["acs_context_coverage"] == "WARN"
    assert statuses["publication_status"] == "BLOCKER"
    assert statuses["readiness_gates"] == "BLOCKER"


def test_all_states_manifest_blocks_unresolved_acs_and_publication_gates(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "state_scope": "ALL_STATES",
                "publication_status": "not_ready_for_publication",
                "readiness_gates": ["review required"],
                "state_coverage": {
                    "states": 51,
                    "states_with_all_public_no_secret_sources": 51,
                    "states_with_acs_county_context": 0,
                    "states_with_acs_tract_context": 0,
                },
                "state_coverage_gaps": missing_acs_gaps(),
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report = audit_all_states_manifest(manifest)
    statuses = dict(zip(report["check"], report["status"], strict=True))

    assert statuses["state_scope"] == "PASS"
    assert statuses["public_source_coverage"] == "PASS"
    assert statuses["acs_context_coverage"] == "BLOCKER"
    assert statuses["publication_status"] == "BLOCKER"
    assert statuses["readiness_gates"] == "BLOCKER"


def test_readiness_json_must_be_ready_for_production(tmp_path: Path) -> None:
    readiness = tmp_path / "readiness.json"
    readiness.write_text(
        json.dumps(
            {
                "overall_status": "BLOCKED",
                "checks": [{"status": "BLOCKER"}, {"status": "WARN"}],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report = audit_readiness_json(readiness)

    assert report.loc[0, "status"] == "BLOCKER"
    assert "1 blocker" in report.loc[0, "details"]


def test_run_production_audit_combines_config_package_and_readiness(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = tmp_path / "config.toml"
    config.write_text(_config_toml(required_env='["CENSUS_API_KEY"]'), encoding="utf-8")
    monkeypatch.setenv("CENSUS_API_KEY", "test-key")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(_ready_manifest()) + "\n", encoding="utf-8")
    readiness = tmp_path / "readiness.json"
    readiness.write_text(
        json.dumps({"overall_status": "READY", "checks": []}) + "\n",
        encoding="utf-8",
    )

    report = run_production_audit(
        config_path=config,
        all_states_manifest=manifest,
        readiness_json=readiness,
    )

    assert production_overall_status(report) == "READY"
    assert set(report["status"]) == {"PASS"}


def missing_acs_gaps() -> dict[str, list[str]]:
    return {
        "missing_mqsa_rows": [],
        "missing_hrsa_candidates": [],
        "missing_places_rows": [],
        "missing_census_counties": [],
        "missing_census_tracts": [],
        "missing_cdc_atsdr_svi_counties": [],
        "missing_any_public_no_secret_source": [],
        "missing_acs_county_context": ["AL"],
        "missing_acs_tract_context": ["AL"],
    }


def _config_toml(
    *,
    required_env: str,
    mqsa_snapshot_owners: str = '["@AKaturu"]',
) -> str:
    return f"""
[credentials]
required_env = {required_env}

[review.owners]
mqsa_snapshot = {mqsa_snapshot_owners}
geocoding = ["@AKaturu"]
routing = ["@AKaturu"]
candidate_sites = ["@AKaturu"]
publication = ["@AKaturu"]

[routing]
provider = "self-hosted-osrm"
profile = "driving"
traffic_assumption = "free-flow"
matrix_metadata_json = "matrix.metadata.json"
""".strip()


def _ready_manifest() -> dict[str, object]:
    return {
        "state_scope": "ALL_STATES",
        "publication_status": "ready_for_publication",
        "readiness_gates": [],
        "state_coverage": {
            "states": 51,
            "states_with_all_public_no_secret_sources": 51,
            "states_with_acs_county_context": 51,
            "states_with_acs_tract_context": 51,
        },
        "state_coverage_gaps": {
            "missing_mqsa_rows": [],
            "missing_hrsa_candidates": [],
            "missing_places_rows": [],
            "missing_census_counties": [],
            "missing_census_tracts": [],
            "missing_cdc_atsdr_svi_counties": [],
            "missing_any_public_no_secret_source": [],
            "missing_acs_county_context": [],
            "missing_acs_tract_context": [],
        },
    }
