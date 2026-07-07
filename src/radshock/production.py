from __future__ import annotations

import json
import os
import tomllib
from pathlib import Path
from typing import Any, Literal

import pandas as pd

ProductionStatus = Literal["PASS", "WARN", "BLOCKER"]
OverallProductionStatus = Literal["READY", "WARN", "BLOCKED"]

PRODUCTION_CHECK_COLUMNS = ["domain", "check", "value", "status", "details"]
PUBLIC_GAP_KEYS = [
    "missing_mqsa_rows",
    "missing_hrsa_candidates",
    "missing_places_rows",
    "missing_census_counties",
    "missing_census_tracts",
    "missing_cdc_atsdr_svi_counties",
    "missing_any_public_no_secret_source",
]


def run_production_audit(
    *,
    config_path: Path,
    all_states_manifest: Path | None = None,
    readiness_json: Path | None = None,
    require_acs: bool = True,
) -> pd.DataFrame:
    """Build a project-level production completion audit."""
    frames = [audit_production_config(config_path)]
    if all_states_manifest is None:
        frames.append(
            pd.DataFrame(
                [
                    _row(
                        "all_states_package",
                        "manifest",
                        "missing",
                        "BLOCKER",
                        "Pass --all-states-manifest for the staged all-50-state data package.",
                    )
                ],
                columns=PRODUCTION_CHECK_COLUMNS,
            )
        )
    else:
        frames.append(audit_all_states_manifest(all_states_manifest, require_acs=require_acs))

    if readiness_json is None:
        frames.append(
            pd.DataFrame(
                [
                    _row(
                        "analysis_readiness",
                        "readiness_json",
                        "missing",
                        "BLOCKER",
                        "Pass --readiness-json from a reviewed analysis package.",
                    )
                ],
                columns=PRODUCTION_CHECK_COLUMNS,
            )
        )
    else:
        frames.append(audit_readiness_json(readiness_json))
    return pd.concat(frames, ignore_index=True)


def audit_production_config(config_path: Path) -> pd.DataFrame:
    """Audit review-owner and production credential configuration.

    Secrets are checked by environment-variable presence only; secret values are never returned.
    """
    if not config_path.exists():
        return pd.DataFrame(
            [
                _row(
                    "configuration",
                    "config_file",
                    str(config_path),
                    "BLOCKER",
                    "Production configuration file does not exist.",
                )
            ],
            columns=PRODUCTION_CHECK_COLUMNS,
        )
    try:
        payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        return pd.DataFrame(
            [
                _row(
                    "configuration",
                    "config_file",
                    str(config_path),
                    "BLOCKER",
                    f"Production configuration is not valid TOML: {exc}",
                )
            ],
            columns=PRODUCTION_CHECK_COLUMNS,
        )

    rows: list[dict[str, object]] = []
    review = payload.get("review", {})
    owners = review.get("owners", {}) if isinstance(review, dict) else {}
    for key in ["mqsa_snapshot", "geocoding", "routing", "candidate_sites", "publication"]:
        value = owners.get(key, []) if isinstance(owners, dict) else []
        owners_list = _string_list(value)
        rows.append(
            _row(
                "review_owner",
                key,
                len(owners_list),
                "PASS" if owners_list else "BLOCKER",
                "Owner configured." if owners_list else "At least one named owner is required.",
            )
        )

    credentials = payload.get("credentials", {})
    if not isinstance(credentials, dict):
        credentials = {}
    required_envs = _string_list(credentials.get("required_env", []))
    if not required_envs:
        rows.append(
            _row(
                "credential",
                "required_env",
                0,
                "WARN",
                "No required production credential environment variables are configured.",
            )
        )
    for env_name in required_envs:
        present = bool(os.getenv(env_name, "").strip())
        rows.append(
            _row(
                "credential",
                env_name,
                "set" if present else "missing",
                "PASS" if present else "BLOCKER",
                "Environment variable is present."
                if present
                else "Set this environment variable in GitHub secrets or the local runner.",
            )
        )

    routing = payload.get("routing", {})
    if not isinstance(routing, dict):
        routing = {}
    for key in ["provider", "profile", "traffic_assumption", "matrix_metadata_json"]:
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
    return pd.DataFrame(rows, columns=PRODUCTION_CHECK_COLUMNS)


def audit_all_states_manifest(manifest_path: Path, *, require_acs: bool = True) -> pd.DataFrame:
    """Audit the all-50-state staging package manifest for production launch gates."""
    payload = _load_json_object(manifest_path, domain="all_states_package")
    if isinstance(payload, pd.DataFrame):
        return payload
    rows: list[dict[str, object]] = []
    coverage = payload.get("state_coverage", {})
    if not isinstance(coverage, dict):
        coverage = {}
    gaps = payload.get("state_coverage_gaps", {})
    if not isinstance(gaps, dict):
        gaps = {}

    state_scope = str(payload.get("state_scope", ""))
    rows.append(
        _row(
            "all_states_package",
            "state_scope",
            state_scope,
            "PASS" if state_scope == "ALL_STATES" else "BLOCKER",
            "Package is scoped to all states."
            if state_scope == "ALL_STATES"
            else "Regenerate the data package with the all-state scope.",
        )
    )
    state_count = _int_value(coverage.get("states"))
    rows.append(
        _row(
            "all_states_package",
            "state_count",
            state_count,
            "PASS" if state_count == 51 else "BLOCKER",
            "Manifest reports 51 states."
            if state_count == 51
            else "Manifest must report 51 states (50 states + DC) before production.",
        )
    )

    public_gap_count = sum(len(_string_list(gaps.get(key, []))) for key in PUBLIC_GAP_KEYS)
    public_source_states = _int_value(coverage.get("states_with_all_public_no_secret_sources"))
    rows.append(
        _row(
            "all_states_package",
            "public_source_coverage",
            public_source_states,
            "PASS" if public_gap_count == 0 and public_source_states == 51 else "BLOCKER",
            "No public no-secret source state gaps detected."
            if public_gap_count == 0 and public_source_states == 51
            else "Refresh or review source inputs until all 51-state public sources are covered.",
        )
    )

    acs_counties = _int_value(coverage.get("states_with_acs_county_context"))
    acs_tracts = _int_value(coverage.get("states_with_acs_tract_context"))
    acs_complete = acs_counties == 51 and acs_tracts == 51
    rows.append(
        _row(
            "all_states_package",
            "acs_context_coverage",
            f"county={acs_counties}; tract={acs_tracts}",
            "PASS" if acs_complete else ("BLOCKER" if require_acs else "WARN"),
            "ACS county and tract context covers all states."
            if acs_complete
            else "Set CENSUS_API_KEY and rebuild the package to add all-state ACS context.",
        )
    )

    publication_status = str(payload.get("publication_status", ""))
    publication_ready = publication_status in {
        "ready",
        "ready_for_publication",
        "publication_ready",
    }
    rows.append(
        _row(
            "all_states_package",
            "publication_status",
            publication_status or "missing",
            "PASS" if publication_ready else "BLOCKER",
            "Package manifest is marked ready for publication."
            if publication_ready
            else "Package manifest is not marked ready for publication.",
        )
    )

    readiness_gates = _string_list(payload.get("readiness_gates", []))
    details = (
        "No unresolved all-state package readiness gates."
        if not readiness_gates
        else (
            f"Resolve {len(readiness_gates)} manifest readiness gate(s): "
            + "; ".join(readiness_gates[:10])
            + ("; ..." if len(readiness_gates) > 10 else "")
            + "."
        )
    )
    rows.append(
        _row(
            "all_states_package",
            "readiness_gates",
            len(readiness_gates),
            "PASS" if not readiness_gates else "BLOCKER",
            details,
        )
    )
    return pd.DataFrame(rows, columns=PRODUCTION_CHECK_COLUMNS)


def audit_readiness_json(path: Path) -> pd.DataFrame:
    """Audit a generated readiness_audit.json file for production launch."""
    payload = _load_json_object(path, domain="analysis_readiness")
    if isinstance(payload, pd.DataFrame):
        return payload
    checks = payload.get("checks", [])
    if not isinstance(checks, list):
        checks = []
    overall = str(payload.get("overall_status", "UNKNOWN"))
    blockers = sum(
        isinstance(check, dict) and check.get("status") == "BLOCKER" for check in checks
    )
    warnings = sum(isinstance(check, dict) and check.get("status") == "WARN" for check in checks)
    status: ProductionStatus = "PASS" if overall == "READY" else "BLOCKER"
    if overall == "WARN":
        status = "WARN"
    return pd.DataFrame(
        [
            _row(
                "analysis_readiness",
                "overall_status",
                overall,
                status,
                f"Analysis readiness report has {blockers} blocker(s) and {warnings} warning(s).",
            )
        ],
        columns=PRODUCTION_CHECK_COLUMNS,
    )


def production_overall_status(checks: pd.DataFrame) -> OverallProductionStatus:
    statuses = set(checks["status"].astype(str)) if "status" in checks else set()
    if "BLOCKER" in statuses:
        return "BLOCKED"
    if "WARN" in statuses:
        return "WARN"
    return "READY"


def production_audit_to_json(checks: pd.DataFrame) -> str:
    payload = {
        "overall_status": production_overall_status(checks),
        "blockers": int((checks["status"] == "BLOCKER").sum()),
        "warnings": int((checks["status"] == "WARN").sum()),
        "checks": checks.to_dict(orient="records"),
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def render_production_audit_markdown(checks: pd.DataFrame) -> str:
    lines = [
        "# Production Completion Audit",
        "",
        f"**Overall status:** {production_overall_status(checks)}",
        f"**Blockers:** {int((checks['status'] == 'BLOCKER').sum())}",
        f"**Warnings:** {int((checks['status'] == 'WARN').sum())}",
        "",
        "| Domain | Check | Status | Value | Details |",
        "|---|---|---|---|---|",
    ]
    for row in checks.itertuples(index=False):
        lines.append(
            f"| `{row.domain}` | `{row.check}` | {row.status} | "
            f"{_markdown_escape(str(row.value))} | {_markdown_escape(str(row.details))} |"
        )
    return "\n".join(lines).strip() + "\n"


def _load_json_object(path: Path, *, domain: str) -> dict[str, Any] | pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(
            [
                _row(
                    domain,
                    "json_file",
                    str(path),
                    "BLOCKER",
                    "Required JSON file does not exist.",
                )
            ],
            columns=PRODUCTION_CHECK_COLUMNS,
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return pd.DataFrame(
            [
                _row(
                    domain,
                    "json_file",
                    str(path),
                    "BLOCKER",
                    f"JSON file could not be parsed: {exc}",
                )
            ],
            columns=PRODUCTION_CHECK_COLUMNS,
        )
    if not isinstance(payload, dict):
        return pd.DataFrame(
            [
                _row(domain, "json_file", str(path), "BLOCKER", "JSON payload must be an object.")
            ],
            columns=PRODUCTION_CHECK_COLUMNS,
        )
    return payload


def _row(
    domain: str,
    check: str,
    value: object,
    status: ProductionStatus,
    details: str,
) -> dict[str, object]:
    return {
        "domain": domain,
        "check": check,
        "value": value,
        "status": status,
        "details": details,
    }


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _int_value(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _markdown_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
