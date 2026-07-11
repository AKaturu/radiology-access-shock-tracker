from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import pandas as pd

from radshock.schemas import require_columns, validate_facilities
from radshock.snapshots import file_sha256

CheckStatus = Literal["PASS", "WARN", "BLOCKER"]
OverallStatus = Literal["READY", "WARN", "BLOCKED"]


@dataclass(frozen=True)
class AuditCheck:
    """One production-readiness finding."""

    check_id: str
    label: str
    status: CheckStatus
    details: str
    recommendation: str


@dataclass(frozen=True)
class ReadinessAudit:
    """Production readiness audit result."""

    overall_status: OverallStatus
    generated_at_utc: str
    analysis_dir: str
    checks: list[AuditCheck]

    def to_dict(self) -> dict[str, object]:
        return {
            "overall_status": self.overall_status,
            "generated_at_utc": self.generated_at_utc,
            "analysis_dir": self.analysis_dir,
            "checks": [asdict(check) for check in self.checks],
        }


def run_readiness_audit(
    analysis_dir: Path,
    before_snapshot_dir: Path | None = None,
    after_snapshot_dir: Path | None = None,
    raw_source_metadata: Path | None = None,
    require_travel_time: bool = False,
) -> ReadinessAudit:
    """Audit whether an analysis package is ready for real-world publication review."""
    checks: list[AuditCheck] = []
    if not analysis_dir.exists() or not analysis_dir.is_dir():
        checks.append(
            AuditCheck(
                "analysis_dir",
                "Analysis directory",
                "BLOCKER",
                f"Analysis directory does not exist: {analysis_dir}",
                "Run radshock analyze or radshock demo before auditing outputs.",
            )
        )
        return _audit(analysis_dir, checks)

    checks.append(
        AuditCheck(
            "analysis_dir",
            "Analysis directory",
            "PASS",
            f"Found analysis directory: {analysis_dir}",
            "No action required.",
        )
    )
    manifest = _audit_manifest(analysis_dir, checks)
    events = _audit_events(analysis_dir / "facility_events.csv", checks)
    shocks = _audit_county_shocks(analysis_dir / "county_shocks.csv", checks)
    _audit_interventions(analysis_dir / "intervention_rankings.csv", checks)
    _audit_sensitivity(analysis_dir / "sensitivity_analysis.csv", checks)
    _audit_brief(analysis_dir, checks)
    if shocks is not None:
        _audit_travel_time(shocks, checks, require_travel_time=require_travel_time)
        _audit_route_provider(manifest, shocks, checks, require_travel_time=require_travel_time)
    if events is not None and shocks is not None:
        _audit_events_against_shocks(events, shocks, checks)
    _audit_snapshot("before", before_snapshot_dir, checks)
    _audit_snapshot("after", after_snapshot_dir, checks)
    _audit_raw_source_metadata(raw_source_metadata, checks)
    return _audit(analysis_dir, checks)


def find_manifest_path(analysis_dir: Path) -> Path | None:
    """Find the manifest for either a package root or direct analysis output directory."""
    for path in [analysis_dir / "manifest.json", analysis_dir.parent / "manifest.json"]:
        if path.exists():
            return path
    return None


def render_readiness_markdown(audit: ReadinessAudit) -> str:
    """Render a concise human-readable readiness report."""
    lines = [
        "# Production Readiness Audit",
        "",
        f"**Overall status:** {audit.overall_status}",
        f"**Generated at:** {audit.generated_at_utc}",
        f"**Analysis directory:** `{audit.analysis_dir}`",
        "",
        "## Checks",
        "",
    ]
    for check in audit.checks:
        lines.extend(
            [
                f"### {check.status}: {check.label}",
                "",
                check.details,
                "",
                f"Recommendation: {check.recommendation}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def audit_to_json(audit: ReadinessAudit) -> str:
    return json.dumps(audit.to_dict(), indent=2, sort_keys=True) + "\n"


def _audit(analysis_dir: Path, checks: list[AuditCheck]) -> ReadinessAudit:
    if any(check.status == "BLOCKER" for check in checks):
        overall: OverallStatus = "BLOCKED"
    elif any(check.status == "WARN" for check in checks):
        overall = "WARN"
    else:
        overall = "READY"
    return ReadinessAudit(
        overall_status=overall,
        generated_at_utc=datetime.now(UTC).isoformat(),
        analysis_dir=str(analysis_dir),
        checks=checks,
    )


def _audit_manifest(analysis_dir: Path, checks: list[AuditCheck]) -> dict[str, object] | None:
    manifest_path = find_manifest_path(analysis_dir)
    if manifest_path is None:
        checked_paths = [analysis_dir / "manifest.json", analysis_dir.parent / "manifest.json"]
        checks.append(
            AuditCheck(
                "manifest",
                "Manifest provenance",
                "WARN",
                "No manifest found at: " + ", ".join(str(path) for path in checked_paths),
                "Store a manifest with synthetic_data and source provenance before publication.",
            )
        )
        return None
    try:
        manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        checks.append(
            AuditCheck(
                "manifest",
                "Manifest provenance",
                "BLOCKER",
                f"Manifest is not valid JSON: {exc}",
                "Regenerate the manifest or repair the JSON before publication.",
            )
        )
        return None
    if not isinstance(manifest_payload, dict):
        checks.append(
            AuditCheck(
                "manifest",
                "Manifest provenance",
                "BLOCKER",
                "Manifest JSON must be an object.",
                "Regenerate the manifest before publication.",
            )
        )
        return None
    manifest: dict[str, object] = manifest_payload
    if bool(manifest.get("synthetic_data")):
        checks.append(
            AuditCheck(
                "manifest",
                "Manifest provenance",
                "BLOCKER",
                "Manifest marks this analysis as synthetic demonstration data.",
                "Run the pipeline on reviewed real source data before publication.",
            )
        )
    else:
        checks.append(
            AuditCheck(
                "manifest",
                "Manifest provenance",
                "PASS",
                f"Manifest is present at {manifest_path} and does not mark the analysis "
                "as synthetic.",
                "No action required.",
            )
        )
    return manifest


def _audit_events(path: Path, checks: list[AuditCheck]) -> pd.DataFrame | None:
    if not path.exists():
        checks.append(
            AuditCheck(
                "facility_events",
                "Facility events",
                "BLOCKER",
                f"Missing required facility events file: {path}",
                "Run snapshot comparison before publication.",
            )
        )
        return None
    try:
        events = pd.read_csv(path)
        require_columns(events, {"event_type"}, "facility events")
    except Exception as exc:
        checks.append(
            AuditCheck(
                "facility_events",
                "Facility events",
                "BLOCKER",
                f"Facility events file could not be read or validated: {exc}",
                "Regenerate facility_events.csv from validated snapshots.",
            )
        )
        return None
    if "CLOSED" in set(events["event_type"].astype(str)):
        checks.append(
            AuditCheck(
                "facility_events",
                "Facility events",
                "BLOCKER",
                "Facility events contain CLOSED claims.",
                "Use POSSIBLE_CLOSURE until closure has independent verification.",
            )
        )
        return events
    if events.empty:
        checks.append(
            AuditCheck(
                "facility_events",
                "Facility events",
                "PASS",
                "Facility events file is present and contains no event signals.",
                "No action required.",
            )
        )
        return events
    if "requires_verification" not in events.columns:
        checks.append(
            AuditCheck(
                "facility_events",
                "Facility events",
                "WARN",
                "Facility events lack a requires_verification column.",
                "Keep verification status with every event before publication.",
            )
        )
        return events
    unresolved = events["requires_verification"].map(_coerce_bool).fillna(True)
    unresolved_count = int(unresolved.sum())
    if unresolved_count:
        checks.append(
            AuditCheck(
                "facility_events",
                "Facility events",
                "BLOCKER",
                f"{unresolved_count} facility event signals still require verification.",
                "Verify high-severity events with primary sources and set verified rows false.",
            )
        )
    else:
        checks.append(
            AuditCheck(
                "facility_events",
                "Facility events",
                "PASS",
                f"{len(events)} facility event rows are marked verified.",
                "No action required.",
            )
        )
    return events


def _audit_county_shocks(path: Path, checks: list[AuditCheck]) -> pd.DataFrame | None:
    if not path.exists():
        checks.append(
            AuditCheck(
                "county_shocks",
                "County shocks",
                "BLOCKER",
                f"Missing required county shocks file: {path}",
                "Run radshock analyze or compare-travel-time-access before publication.",
            )
        )
        return None
    try:
        shocks = pd.read_csv(path, dtype={"county_fips": str})
        require_columns(
            shocks,
            {"county_fips", "county_name", "shock_score", "alert_level"},
            "county shocks",
        )
        shocks["shock_score"] = pd.to_numeric(shocks["shock_score"], errors="raise")
    except Exception as exc:
        checks.append(
            AuditCheck(
                "county_shocks",
                "County shocks",
                "BLOCKER",
                f"County shocks file could not be read or validated: {exc}",
                "Regenerate county_shocks.csv from validated inputs.",
            )
        )
        return None
    if shocks.empty:
        checks.append(
            AuditCheck(
                "county_shocks",
                "County shocks",
                "WARN",
                "County shocks file is present but empty.",
                "Confirm the analysis geography and population inputs before publication.",
            )
        )
        return shocks
    flagged = int(shocks["alert_level"].astype(str).isin(["WARNING", "CRITICAL"]).sum())
    checks.append(
        AuditCheck(
            "county_shocks",
            "County shocks",
            "PASS",
            f"County shocks file has {len(shocks)} rows; {flagged} warning or critical.",
            "No action required.",
        )
    )
    return shocks


def _audit_interventions(path: Path, checks: list[AuditCheck]) -> None:
    if not path.exists():
        checks.append(
            AuditCheck(
                "interventions",
                "Intervention rankings",
                "WARN",
                f"No intervention rankings file found at {path}.",
                "Generate intervention rankings before using the package for response planning.",
            )
        )
        return
    interventions = pd.read_csv(path)
    rows = len(interventions)
    placeholder_mask = pd.Series(False, index=interventions.index)
    if "candidate_id" in interventions.columns:
        placeholder_mask |= (
            interventions["candidate_id"].astype(str).str.startswith("COUNTY-CENTROID-")
        )
    if "candidate_name" in interventions.columns:
        placeholder_mask |= (
            interventions["candidate_name"]
            .astype(str)
            .str.contains(
                "County Centroid",
                case=False,
                na=False,
            )
        )
    placeholder_count = int(placeholder_mask.sum())
    if placeholder_count:
        checks.append(
            AuditCheck(
                "interventions",
                "Intervention rankings",
                "WARN",
                f"Intervention rankings include {placeholder_count} county-centroid "
                "placeholder candidate(s).",
                "Replace placeholders with reviewed mobile-stop or fixed-site assumptions "
                "before using intervention rankings for operational planning.",
            )
        )
        return
    checks.append(
        AuditCheck(
            "interventions",
            "Intervention rankings",
            "PASS" if rows else "WARN",
            f"Intervention rankings file has {rows} rows.",
            "No action required." if rows else "Add candidate sites before response planning.",
        )
    )


def _audit_sensitivity(path: Path, checks: list[AuditCheck]) -> None:
    if not path.exists():
        checks.append(
            AuditCheck(
                "sensitivity",
                "Sensitivity analysis",
                "WARN",
                f"No sensitivity analysis file found at {path}.",
                "Run radshock sensitivity-analysis before relying on score rankings.",
            )
        )
        return
    try:
        sensitivity = pd.read_csv(path)
        require_columns(sensitivity, {"scenario_id", "county_fips"}, "sensitivity analysis")
        scenarios = int(sensitivity["scenario_id"].nunique())
    except Exception as exc:
        checks.append(
            AuditCheck(
                "sensitivity",
                "Sensitivity analysis",
                "WARN",
                f"Sensitivity analysis could not be read or validated: {exc}",
                "Regenerate sensitivity_analysis.csv from county_shocks.csv.",
            )
        )
        return
    checks.append(
        AuditCheck(
            "sensitivity",
            "Sensitivity analysis",
            "PASS" if scenarios >= 2 else "WARN",
            f"Sensitivity analysis covers {scenarios} scenario(s).",
            "No action required."
            if scenarios >= 2
            else "Use multiple scenarios for robustness checks.",
        )
    )


def _audit_brief(analysis_dir: Path, checks: list[AuditCheck]) -> None:
    candidates = [
        analysis_dir / "policy_brief.md",
        analysis_dir.parent / "briefs" / "policy_brief.md",
    ]
    if any(path.exists() for path in candidates):
        checks.append(
            AuditCheck(
                "policy_brief",
                "Policy brief",
                "PASS",
                "Policy brief Markdown output is present.",
                "No action required.",
            )
        )
    else:
        checks.append(
            AuditCheck(
                "policy_brief",
                "Policy brief",
                "WARN",
                "Policy brief Markdown output is missing.",
                "Generate a policy brief before sharing nontechnical findings.",
            )
        )


def _audit_travel_time(
    shocks: pd.DataFrame,
    checks: list[AuditCheck],
    require_travel_time: bool,
) -> None:
    metric_values = set(shocks.get("access_metric", pd.Series(dtype=str)).astype(str))
    has_travel_time = "travel_time_minutes" in metric_values or {
        "mean_travel_time_minutes_before",
        "mean_travel_time_minutes_after",
    }.issubset(shocks.columns)
    if not has_travel_time:
        checks.append(
            AuditCheck(
                "travel_time",
                "Travel-time analysis",
                "BLOCKER" if require_travel_time else "WARN",
                "County shocks do not appear to use reviewed travel-time matrices.",
                "Run compare-travel-time-access when road-time estimates are required.",
            )
        )
        return
    coverage_columns = [
        column
        for column in ["travel_time_coverage_before", "travel_time_coverage_after"]
        if column in shocks.columns
    ]
    if not coverage_columns:
        checks.append(
            AuditCheck(
                "travel_time",
                "Travel-time analysis",
                "WARN",
                "Travel-time output is present but coverage columns are missing.",
                "Regenerate travel-time shocks with the current CLI before publication.",
            )
        )
        return
    minimum_coverage = min(
        float(pd.to_numeric(shocks[column], errors="coerce").min()) for column in coverage_columns
    )
    checks.append(
        AuditCheck(
            "travel_time",
            "Travel-time analysis",
            "PASS" if minimum_coverage >= 0.95 else "WARN",
            f"Minimum county travel-time route coverage is {minimum_coverage:.1%}.",
            "No action required."
            if minimum_coverage >= 0.95
            else "Review missing routes and routing assumptions.",
        )
    )


def _audit_route_provider(
    manifest: dict[str, object] | None,
    shocks: pd.DataFrame,
    checks: list[AuditCheck],
    require_travel_time: bool,
) -> None:
    metric_values = set(shocks.get("access_metric", pd.Series(dtype=str)).astype(str))
    has_travel_time = "travel_time_minutes" in metric_values or {
        "mean_travel_time_minutes_before",
        "mean_travel_time_minutes_after",
    }.issubset(shocks.columns)
    if not has_travel_time:
        return
    routing = manifest.get("routing") if manifest is not None else None
    if not isinstance(routing, dict):
        checks.append(
            AuditCheck(
                "route_provider",
                "Route provider provenance",
                "BLOCKER" if require_travel_time else "WARN",
                "Travel-time outputs are present, but the manifest does not record routing "
                "provider provenance.",
                "Record provider, endpoint, profile, network vintage, traffic assumptions, "
                "and matrix metadata before publication review.",
            )
        )
        return
    provider_text = " ".join(
        str(routing.get(key, ""))
        for key in ["provider", "route_source_url", "matrix_metadata_json", "note"]
    ).lower()
    if "router.project-osrm.org" in provider_text or (
        "osrm" in provider_text and "public" in provider_text
    ):
        checks.append(
            AuditCheck(
                "route_provider",
                "Route provider provenance",
                "BLOCKER",
                "Travel-time outputs use the public OSRM-compatible endpoint, which is a "
                "testing service without production uptime or network-vintage guarantees.",
                "Regenerate route matrices with a reviewed production provider or self-hosted "
                "routing engine before publishing road-time findings.",
            )
        )
        return
    missing_fields = _missing_route_provenance_fields(routing)
    if missing_fields:
        checks.append(
            AuditCheck(
                "route_provider",
                "Route provider provenance",
                "BLOCKER" if require_travel_time else "WARN",
                "Travel-time routing provenance is incomplete; missing: "
                + ", ".join(missing_fields),
                "Record provider, profile, self-hosted/commercial deployment, engine version, "
                "map extract source/date/checksum, and traffic assumptions before publication.",
            )
        )
        return
    checks.append(
        AuditCheck(
            "route_provider",
            "Route provider provenance",
            "PASS",
            "Manifest records routing provider provenance for travel-time outputs.",
            "Review provider terms, profile, network vintage, and traffic assumptions before "
            "publication.",
        )
    )


def _missing_route_provenance_fields(routing: dict[str, object]) -> list[str]:
    missing: list[str] = []
    for field in ["provider", "profile", "route_source_url", "matrix_metadata_json"]:
        if not str(routing.get(field, "")).strip():
            missing.append(f"routing.{field}")
    if not str(routing.get("traffic_assumption", "")).strip():
        missing.append("routing.traffic_assumption")

    engine = routing.get("engine")
    if not isinstance(engine, dict):
        missing.extend(
            [
                "routing.engine.name",
                "routing.engine.version",
                "routing.engine.deployment",
            ]
        )
    else:
        for field in ["name", "version", "deployment"]:
            if not str(engine.get(field, "")).strip():
                missing.append(f"routing.engine.{field}")

    map_extract = routing.get("map_extract")
    if not isinstance(map_extract, dict):
        missing.extend(
            [
                "routing.map_extract.source_url",
                "routing.map_extract.osm_data_timestamp",
                "routing.map_extract.sha256",
            ]
        )
    else:
        for field in ["source_url", "osm_data_timestamp", "sha256"]:
            if not str(map_extract.get(field, "")).strip():
                missing.append(f"routing.map_extract.{field}")
    return missing


def _audit_events_against_shocks(
    events: pd.DataFrame,
    shocks: pd.DataFrame,
    checks: list[AuditCheck],
) -> None:
    flagged = shocks["alert_level"].astype(str).isin(["WARNING", "CRITICAL"]).any()
    if not flagged:
        checks.append(
            AuditCheck(
                "event_shock_alignment",
                "Event and shock alignment",
                "PASS",
                "No warning or critical county shocks require event-review escalation.",
                "No action required.",
            )
        )
        return
    if events.empty:
        checks.append(
            AuditCheck(
                "event_shock_alignment",
                "Event and shock alignment",
                "WARN",
                "County shocks are flagged but no facility event rows are present.",
                "Confirm whether shocks came from route or population changes rather "
                "than facility events.",
            )
        )
        return
    checks.append(
        AuditCheck(
            "event_shock_alignment",
            "Event and shock alignment",
            "PASS",
            "County shock outputs and facility event outputs are both present.",
            "Review high-priority counties against verified facility events before publication.",
        )
    )


def _audit_snapshot(label: str, snapshot_dir: Path | None, checks: list[AuditCheck]) -> None:
    check_id = f"{label}_snapshot"
    title = f"{label.title()} snapshot"
    if snapshot_dir is None:
        checks.append(
            AuditCheck(
                check_id,
                title,
                "WARN",
                f"No {label} snapshot directory was supplied.",
                "Pass snapshot directories to readiness-audit to verify snapshot provenance.",
            )
        )
        return
    facilities_path = snapshot_dir / "facilities.csv"
    metadata_path = snapshot_dir / "metadata.json"
    if not facilities_path.exists() or not metadata_path.exists():
        checks.append(
            AuditCheck(
                check_id,
                title,
                "BLOCKER",
                f"Snapshot is missing facilities.csv or metadata.json: {snapshot_dir}",
                "Store snapshots with radshock ingest-snapshot before publication.",
            )
        )
        return
    try:
        facilities = validate_facilities(pd.read_csv(facilities_path))
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except Exception as exc:
        checks.append(
            AuditCheck(
                check_id,
                title,
                "BLOCKER",
                f"Snapshot could not be validated: {exc}",
                "Regenerate the snapshot from a reviewed facility CSV.",
            )
        )
        return
    if str(metadata.get("sha256", "")) != file_sha256(facilities_path):
        checks.append(
            AuditCheck(
                check_id,
                title,
                "BLOCKER",
                f"Snapshot checksum does not match metadata: {snapshot_dir}",
                "Regenerate metadata or investigate snapshot modification.",
            )
        )
        return
    if (
        bool(metadata.get("synthetic_data"))
        or "synthetic" in str(metadata.get("source_name", "")).lower()
    ):
        checks.append(
            AuditCheck(
                check_id,
                title,
                "BLOCKER",
                f"Snapshot metadata indicates synthetic source data: {snapshot_dir}",
                "Use reviewed real source snapshots before publication.",
            )
        )
        return
    missing_provenance = [
        key for key in ["source_name", "source_url", "raw_source_sha256"] if not metadata.get(key)
    ]
    if missing_provenance:
        checks.append(
            AuditCheck(
                check_id,
                title,
                "WARN",
                f"Snapshot has {len(facilities)} records but is missing provenance: "
                f"{missing_provenance}",
                "Include source URL and raw-source checksum metadata before publication.",
            )
        )
        return
    checks.append(
        AuditCheck(
            check_id,
            title,
            "PASS",
            f"Snapshot has {len(facilities)} validated records and matching checksum metadata.",
            "No action required.",
        )
    )


def _audit_raw_source_metadata(path: Path | None, checks: list[AuditCheck]) -> None:
    if path is None:
        checks.append(
            AuditCheck(
                "raw_source",
                "Raw source archive",
                "WARN",
                "No raw-source metadata file was supplied.",
                "Pass the archived source metadata JSON to verify raw-source provenance.",
            )
        )
        return
    if not path.exists():
        checks.append(
            AuditCheck(
                "raw_source",
                "Raw source archive",
                "BLOCKER",
                f"Raw-source metadata file does not exist: {path}",
                "Archive raw source inputs with radshock fetch-source or archive-source.",
            )
        )
        return
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        checks.append(
            AuditCheck(
                "raw_source",
                "Raw source archive",
                "BLOCKER",
                f"Raw-source metadata is not valid JSON: {exc}",
                "Regenerate raw-source archive metadata.",
            )
        )
        return
    missing = [
        key
        for key in ["source_name", "retrieval_date", "retrieval_method", "sha256"]
        if not metadata.get(key)
    ]
    if missing:
        checks.append(
            AuditCheck(
                "raw_source",
                "Raw source archive",
                "WARN",
                f"Raw-source metadata is missing fields: {missing}",
                "Regenerate source metadata with the archive-source or fetch-source command.",
            )
        )
        return
    checks.append(
        AuditCheck(
            "raw_source",
            "Raw source archive",
            "PASS",
            f"Raw-source metadata is present for {metadata['source_name']}.",
            "No action required.",
        )
    )


def _coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"false", "0", "no", "n", ""}:
        return False
    return True
