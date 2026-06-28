from __future__ import annotations

import os
import tomllib
from pathlib import Path

import pandas as pd


def audit_production_config(config_path: Path) -> pd.DataFrame:
    """Audit review-owner and production credential configuration.

    Secrets are checked by environment-variable presence only; secret values are never returned.
    """
    payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    rows: list[dict[str, object]] = []
    review = payload.get("review", {})
    owners = review.get("owners", {}) if isinstance(review, dict) else {}
    for key in ["mqsa_snapshot", "geocoding", "routing", "candidate_sites", "publication"]:
        value = owners.get(key, []) if isinstance(owners, dict) else []
        count = len(value) if isinstance(value, list) else 0
        rows.append(
            _row(
                "review_owner",
                key,
                count,
                "PASS" if count else "BLOCKER",
                "At least one named owner is required." if not count else "Owner configured.",
            )
        )

    credentials = payload.get("credentials", {})
    if not isinstance(credentials, dict):
        credentials = {}
    required_envs = credentials.get("required_env", [])
    if not isinstance(required_envs, list):
        required_envs = []
    for env_name in required_envs:
        present = bool(os.getenv(str(env_name), "").strip())
        rows.append(
            _row(
                "credential",
                str(env_name),
                "set" if present else "missing",
                "PASS" if present else "BLOCKER",
                "Environment variable is present."
                if present
                else "Set this environment variable in GitHub secrets or the local runner.",
            )
        )

    routing = payload.get("routing", {})
    if isinstance(routing, dict):
        for key in [
            "provider",
            "profile",
            "traffic_assumption",
            "matrix_metadata_json",
        ]:
            configured = bool(str(routing.get(key, "")).strip())
            rows.append(
                _row(
                    "routing",
                    key,
                    str(routing.get(key, "")),
                    "PASS" if configured else "WARN",
                    "Routing provenance field configured."
                    if configured
                    else "Configure before production route publication.",
                )
            )
    return pd.DataFrame(rows, columns=["domain", "check", "value", "status", "details"])


def _row(domain: str, check: str, value: object, status: str, details: str) -> dict[str, object]:
    return {
        "domain": domain,
        "check": check,
        "value": value,
        "status": status,
        "details": details,
    }
