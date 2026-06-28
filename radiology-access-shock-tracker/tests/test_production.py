from __future__ import annotations

from pathlib import Path

from radshock.production import audit_production_config


def test_audit_production_config_checks_owners_and_env(tmp_path: Path, monkeypatch) -> None:
    config = tmp_path / "config.toml"
    config.write_text(
        """
[credentials]
required_env = ["CENSUS_API_KEY"]

[review.owners]
mqsa_snapshot = ["Owner"]
geocoding = ["Owner"]
routing = ["Owner"]
candidate_sites = ["Owner"]
publication = ["Owner"]

[routing]
provider = "self-hosted-osrm"
profile = "driving"
traffic_assumption = "free-flow"
matrix_metadata_json = "matrix.metadata.json"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CENSUS_API_KEY", "test-key")

    report = audit_production_config(config)

    assert set(report["status"]) == {"PASS"}


def test_audit_production_config_blocks_missing_owner_and_secret(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text(
        """
[credentials]
required_env = ["MISSING_SECRET"]

[review.owners]
mqsa_snapshot = []
geocoding = ["Owner"]
routing = ["Owner"]
candidate_sites = ["Owner"]
publication = ["Owner"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    report = audit_production_config(config)

    blockers = report[report["status"] == "BLOCKER"]
    assert {"mqsa_snapshot", "MISSING_SECRET"} <= set(blockers["check"])
