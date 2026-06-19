from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Annotated

import pandas as pd
import typer

from radshock.access import compare_county_access, compare_county_travel_time_access
from radshock.adapters.facilities import (
    FDA_MQSA_PUBLIC_ZIP_URL,
    build_mqsa_review_template,
    finalize_mqsa_review,
    read_fda_mqsa_fixed_width,
)
from radshock.briefs import generate_policy_brief, generate_policy_brief_html
from radshock.changes import detect_changes
from radshock.demo import build_demo
from radshock.geocoding import (
    CensusGeocoder,
    GeocodeCache,
    StaticGeocoder,
    geocode_mqsa_review,
)
from radshock.intervention import simulate_candidates
from radshock.readiness import audit_to_json, render_readiness_markdown, run_readiness_audit
from radshock.schemas import validate_facilities
from radshock.sensitivity import run_sensitivity_analysis
from radshock.snapshots import store_snapshot
from radshock.sources import archive_local_source, fetch_url_source
from radshock.travel_times import (
    build_travel_time_review_template,
    finalize_travel_time_review,
)
from radshock.utilization import summarize_utilization_change

app = typer.Typer(help="Radiology Access Shock Tracker command line interface.")


@app.command()
def demo(
    output_dir: Annotated[Path, typer.Option(help="Directory for demo outputs.")] = Path(
        "outputs/demo"
    ),
) -> None:
    """Run the complete synthetic demonstration pipeline."""
    outputs = build_demo(output_dir)
    typer.echo(f"Demo complete: {output_dir.resolve()}")
    for label, path in outputs.items():
        typer.echo(f"  {label}: {path}")


@app.command("ingest-snapshot")
def ingest_snapshot(
    input_csv: Annotated[Path, typer.Argument(exists=True, readable=True)],
    as_of: Annotated[str, typer.Option(help="Snapshot date in YYYY-MM-DD format.")],
    store_dir: Annotated[Path, typer.Option()] = Path("data/snapshots"),
    source_name: Annotated[str, typer.Option()] = "manual-import",
    source_url: Annotated[
        str | None, typer.Option(help="Source URL or source landing page.")
    ] = None,
    raw_source_path: Annotated[Path | None, typer.Option(exists=True, readable=True)] = None,
    schema_version: Annotated[str, typer.Option()] = "facility_snapshot_v1",
    dry_run: Annotated[bool, typer.Option(help="Validate without writing a snapshot.")] = False,
) -> None:
    """Validate and store an immutable facility snapshot."""
    try:
        snapshot_date = date.fromisoformat(as_of)
    except ValueError as exc:
        raise typer.BadParameter("as_of must use YYYY-MM-DD format") from exc
    frame = validate_facilities(pd.read_csv(input_csv))
    if dry_run:
        active_count = int(frame["active"].sum())
        typer.echo(f"Snapshot valid: {len(frame)} records, {active_count} active")
        return
    destination = store_snapshot(
        input_csv,
        snapshot_date,
        store_dir,
        source_name,
        source_url=source_url,
        raw_source_path=raw_source_path,
        schema_version=schema_version,
    )
    typer.echo(f"Stored snapshot: {destination.resolve()}")


@app.command("fetch-source")
def fetch_source(
    url: Annotated[str, typer.Option(help="Source file URL.")],
    source_name: Annotated[str, typer.Option()] = "manual-source",
    output_dir: Annotated[Path, typer.Option()] = Path("data/raw"),
    timeout: Annotated[int, typer.Option()] = 60,
    force: Annotated[bool, typer.Option(help="Overwrite an existing archived source.")] = False,
) -> None:
    """Download a raw source file into the auditable archive."""
    archived = fetch_url_source(url, output_dir, source_name, timeout=timeout, force=force)
    typer.echo(f"Archived source: {archived.resolve()}")
    typer.echo(f"Metadata: {archived.with_suffix(archived.suffix + '.metadata.json').resolve()}")


@app.command("fetch-fda-mqsa")
def fetch_fda_mqsa(
    output_dir: Annotated[Path, typer.Option()] = Path("data/raw"),
    timeout: Annotated[int, typer.Option()] = 60,
    force: Annotated[bool, typer.Option(help="Overwrite an existing archived source.")] = False,
) -> None:
    """Download the FDA MQSA weekly public facility ZIP into the source archive."""
    archived = fetch_url_source(
        FDA_MQSA_PUBLIC_ZIP_URL,
        output_dir,
        "fda-mqsa-public",
        timeout=timeout,
        force=force,
    )
    typer.echo(f"Archived FDA MQSA source: {archived.resolve()}")
    typer.echo(f"Metadata: {archived.with_suffix(archived.suffix + '.metadata.json').resolve()}")


@app.command("archive-source")
def archive_source(
    input_path: Annotated[Path, typer.Argument(exists=True, readable=True)],
    source_name: Annotated[str, typer.Option()],
    output_dir: Annotated[Path, typer.Option()] = Path("data/raw"),
    source_url: Annotated[str | None, typer.Option()] = None,
    force: Annotated[bool, typer.Option(help="Overwrite an existing archived source.")] = False,
) -> None:
    """Archive a manually downloaded source file with checksum metadata."""
    archived = archive_local_source(
        input_path,
        output_dir,
        source_name,
        source_url=source_url,
        force=force,
    )
    typer.echo(f"Archived source: {archived.resolve()}")
    typer.echo(f"Metadata: {archived.with_suffix(archived.suffix + '.metadata.json').resolve()}")


@app.command("prepare-mqsa-review")
def prepare_mqsa_review(
    input_path: Annotated[Path, typer.Argument(exists=True, readable=True)],
    output_csv: Annotated[Path, typer.Option()],
    state: Annotated[str, typer.Option(help="Two-letter state filter.")] = "NC",
    force: Annotated[bool, typer.Option(help="Overwrite an existing review CSV.")] = False,
) -> None:
    """Create a human-review CSV from the FDA MQSA fixed-width source file."""
    if output_csv.exists() and not force:
        raise typer.BadParameter(f"output already exists: {output_csv}")
    raw = read_fda_mqsa_fixed_width(input_path, state=state)
    review = build_mqsa_review_template(raw)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    review.to_csv(output_csv, index=False)
    typer.echo(f"Review template written: {output_csv.resolve()}")
    typer.echo(
        "Review required: facility_id, latitude, longitude, annual_capacity, and active "
        "must be completed before snapshot ingestion."
    )


@app.command("finalize-mqsa-review")
def finalize_mqsa_review_command(
    input_csv: Annotated[Path, typer.Argument(exists=True, readable=True)],
    output_csv: Annotated[Path, typer.Option()],
    force: Annotated[bool, typer.Option(help="Overwrite an existing output CSV.")] = False,
    dry_run: Annotated[bool, typer.Option(help="Validate without writing output.")] = False,
) -> None:
    """Validate a completed MQSA review CSV and write snapshot-ready facilities."""
    if output_csv.exists() and not force and not dry_run:
        raise typer.BadParameter(f"output already exists: {output_csv}")
    reviewed = finalize_mqsa_review(pd.read_csv(input_csv, dtype=str, keep_default_na=False))
    active_count = int(reviewed["active"].sum())
    if dry_run:
        typer.echo(f"MQSA review complete: {len(reviewed)} records, {active_count} active")
        return
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    reviewed.to_csv(output_csv, index=False)
    typer.echo(f"Snapshot-ready facilities written: {output_csv.resolve()}")
    typer.echo(f"Records: {len(reviewed)}; active: {active_count}")


@app.command("geocode-mqsa-review")
def geocode_mqsa_review_command(
    input_csv: Annotated[Path, typer.Argument(exists=True, readable=True)],
    output_csv: Annotated[Path, typer.Option()],
    provider_name: Annotated[str, typer.Option("--provider")] = "census",
    static_csv: Annotated[Path | None, typer.Option(exists=True, readable=True)] = None,
    cache_path: Annotated[Path, typer.Option()] = Path("data/cache/geocoding/census.json"),
    benchmark: Annotated[str, typer.Option()] = "Public_AR_Current",
    timeout: Annotated[int, typer.Option()] = 30,
    limit: Annotated[int | None, typer.Option(help="Maximum rows to attempt.")] = None,
    overwrite_coordinates: Annotated[
        bool, typer.Option(help="Replace existing latitude/longitude values.")
    ] = False,
    force: Annotated[bool, typer.Option(help="Overwrite an existing output CSV.")] = False,
) -> None:
    """Fill MQSA review CSV coordinate candidates with cached geocoder provenance."""
    if output_csv.exists() and not force:
        raise typer.BadParameter(f"output already exists: {output_csv}")
    provider = _build_geocode_provider(provider_name, static_csv, benchmark, timeout)
    cache = None if provider.name == "static" else GeocodeCache(cache_path)
    result = geocode_mqsa_review(
        pd.read_csv(input_csv, dtype=str, keep_default_na=False),
        provider,
        cache=cache,
        overwrite_coordinates=overwrite_coordinates,
        limit=limit,
    )
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_csv, index=False)
    matched = int((result["geocode_status"] == "matched").sum())
    attempted = int(result["geocode_status"].astype(str).str.len().gt(0).sum())
    typer.echo(f"Geocoded review written: {output_csv.resolve()}")
    typer.echo(f"Attempted: {attempted}; matched: {matched}")
    typer.echo("Human review is still required before running finalize-mqsa-review.")


@app.command("validate-snapshot")
def validate_snapshot(
    snapshot_csv: Annotated[Path, typer.Argument(exists=True, readable=True)],
) -> None:
    """Validate a normalized facility snapshot CSV."""
    frame = validate_facilities(pd.read_csv(snapshot_csv))
    typer.echo(f"Snapshot valid: {len(frame)} records, {int(frame['active'].sum())} active")


@app.command("compare-snapshots")
def compare_snapshots(
    before_csv: Annotated[Path, typer.Option(exists=True)],
    after_csv: Annotated[Path, typer.Option(exists=True)],
    output_csv: Annotated[Path | None, typer.Option()] = None,
) -> None:
    """Compare two facility snapshots and optionally write event signals."""
    events = detect_changes(pd.read_csv(before_csv), pd.read_csv(after_csv))
    if output_csv is not None:
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        events.to_csv(output_csv, index=False)
        typer.echo(f"Event signals written: {output_csv.resolve()}")
    else:
        typer.echo(events.to_csv(index=False))


@app.command("compare-travel-time-access")
def compare_travel_time_access_command(
    before_csv: Annotated[Path, typer.Option(exists=True, readable=True)],
    after_csv: Annotated[Path, typer.Option(exists=True, readable=True)],
    population_csv: Annotated[Path, typer.Option(exists=True, readable=True)],
    counties_csv: Annotated[Path, typer.Option(exists=True, readable=True)],
    before_travel_times_csv: Annotated[Path, typer.Option(exists=True, readable=True)],
    after_travel_times_csv: Annotated[Path, typer.Option(exists=True, readable=True)],
    output_csv: Annotated[Path | None, typer.Option()] = None,
    threshold_minutes: Annotated[float, typer.Option()] = 45.0,
    force: Annotated[bool, typer.Option(help="Overwrite an existing output CSV.")] = False,
) -> None:
    """Compare county access using reviewed point-to-facility travel-time matrices."""
    if output_csv is not None and output_csv.exists() and not force:
        raise typer.BadParameter(f"output already exists: {output_csv}")
    shocks = compare_county_travel_time_access(
        pd.read_csv(population_csv, dtype={"point_id": str, "county_fips": str}),
        pd.read_csv(before_csv, dtype={"facility_id": str}),
        pd.read_csv(after_csv, dtype={"facility_id": str}),
        pd.read_csv(counties_csv, dtype={"county_fips": str}),
        pd.read_csv(before_travel_times_csv, dtype={"point_id": str, "facility_id": str}),
        pd.read_csv(after_travel_times_csv, dtype={"point_id": str, "facility_id": str}),
        threshold_minutes=threshold_minutes,
    )
    if output_csv is not None:
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        shocks.to_csv(output_csv, index=False)
        warning_count = int(shocks["alert_level"].isin(["WARNING", "CRITICAL"]).sum())
        typer.echo(f"Travel-time county shocks written: {output_csv.resolve()}")
        typer.echo(f"Records: {len(shocks)}; warning_or_critical: {warning_count}")
    else:
        typer.echo(shocks.to_csv(index=False))


@app.command("prepare-travel-time-review")
def prepare_travel_time_review_command(
    population_csv: Annotated[Path, typer.Option(exists=True, readable=True)],
    facilities_csv: Annotated[Path, typer.Option(exists=True, readable=True)],
    output_csv: Annotated[Path, typer.Option()],
    max_distance_miles: Annotated[
        float | None,
        typer.Option(help="Optional straight-line prefilter for route pairs."),
    ] = None,
    include_inactive: Annotated[
        bool, typer.Option(help="Include inactive facilities in the routing worklist.")
    ] = False,
    force: Annotated[bool, typer.Option(help="Overwrite an existing output CSV.")] = False,
) -> None:
    """Create a point-to-facility routing worklist for external route review."""
    if output_csv.exists() and not force:
        raise typer.BadParameter(f"output already exists: {output_csv}")
    review = build_travel_time_review_template(
        pd.read_csv(population_csv, dtype={"point_id": str, "county_fips": str}),
        pd.read_csv(facilities_csv, dtype={"facility_id": str}),
        active_only=not include_inactive,
        max_distance_miles=max_distance_miles,
    )
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    review.to_csv(output_csv, index=False)
    typer.echo(f"Travel-time review template written: {output_csv.resolve()}")
    typer.echo(f"Route pairs: {len(review)}")
    typer.echo(
        "Fill travel_time_minutes, route_status, route provider metadata, and review_status "
        "before finalizing."
    )


@app.command("finalize-travel-time-review")
def finalize_travel_time_review_command(
    input_csv: Annotated[Path, typer.Argument(exists=True, readable=True)],
    output_csv: Annotated[Path, typer.Option()],
    force: Annotated[bool, typer.Option(help="Overwrite an existing output CSV.")] = False,
    dry_run: Annotated[bool, typer.Option(help="Validate without writing output.")] = False,
) -> None:
    """Validate reviewed route rows and write a travel-time matrix."""
    if output_csv.exists() and not force and not dry_run:
        raise typer.BadParameter(f"output already exists: {output_csv}")
    matrix = finalize_travel_time_review(
        pd.read_csv(input_csv, dtype={"point_id": str, "facility_id": str}, keep_default_na=False)
    )
    if dry_run:
        typer.echo(f"Travel-time review complete: {len(matrix)} routed pairs")
        return
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    matrix.to_csv(output_csv, index=False)
    typer.echo(f"Travel-time matrix written: {output_csv.resolve()}")
    typer.echo(f"Routed pairs: {len(matrix)}")


@app.command("sensitivity-analysis")
def sensitivity_analysis_command(
    county_shocks_csv: Annotated[Path, typer.Argument(exists=True, readable=True)],
    output_csv: Annotated[Path | None, typer.Option()] = None,
    force: Annotated[bool, typer.Option(help="Overwrite an existing output CSV.")] = False,
) -> None:
    """Re-score county shocks under alternative transparent weighting assumptions."""
    if output_csv is not None and output_csv.exists() and not force:
        raise typer.BadParameter(f"output already exists: {output_csv}")
    sensitivity = run_sensitivity_analysis(
        pd.read_csv(county_shocks_csv, dtype={"county_fips": str})
    )
    if output_csv is not None:
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        sensitivity.to_csv(output_csv, index=False)
        scenario_count = int(sensitivity["scenario_id"].nunique())
        typer.echo(f"Sensitivity analysis written: {output_csv.resolve()}")
        typer.echo(f"Rows: {len(sensitivity)}; scenarios: {scenario_count}")
    else:
        typer.echo(sensitivity.to_csv(index=False))


@app.command("readiness-audit")
def readiness_audit_command(
    analysis_dir: Annotated[Path, typer.Option()] = Path("outputs/demo/analysis"),
    before_snapshot_dir: Annotated[Path | None, typer.Option(exists=True, file_okay=False)] = None,
    after_snapshot_dir: Annotated[Path | None, typer.Option(exists=True, file_okay=False)] = None,
    raw_source_metadata: Annotated[Path | None, typer.Option(exists=True, readable=True)] = None,
    output_json: Annotated[Path | None, typer.Option()] = None,
    output_md: Annotated[Path | None, typer.Option()] = None,
    require_travel_time: Annotated[
        bool, typer.Option(help="Block readiness if county shocks are distance-only.")
    ] = False,
    force: Annotated[bool, typer.Option(help="Overwrite existing report files.")] = False,
) -> None:
    """Audit whether analysis outputs are ready for real-world publication review."""
    audit = run_readiness_audit(
        analysis_dir,
        before_snapshot_dir=before_snapshot_dir,
        after_snapshot_dir=after_snapshot_dir,
        raw_source_metadata=raw_source_metadata,
        require_travel_time=require_travel_time,
    )
    if output_json is not None:
        _write_report(output_json, audit_to_json(audit), force)
        typer.echo(f"Readiness JSON written: {output_json.resolve()}")
    if output_md is not None:
        _write_report(output_md, render_readiness_markdown(audit), force)
        typer.echo(f"Readiness report written: {output_md.resolve()}")
    blocker_count = sum(check.status == "BLOCKER" for check in audit.checks)
    warning_count = sum(check.status == "WARN" for check in audit.checks)
    typer.echo(
        f"Readiness status: {audit.overall_status}; "
        f"blockers: {blocker_count}; warnings: {warning_count}"
    )


def _build_geocode_provider(
    provider_name: str,
    static_csv: Path | None,
    benchmark: str,
    timeout: int,
) -> CensusGeocoder | StaticGeocoder:
    normalized = provider_name.strip().lower()
    if normalized == "census":
        return CensusGeocoder(benchmark=benchmark, timeout=timeout)
    if normalized == "static":
        if static_csv is None:
            raise typer.BadParameter("--static-csv is required when --provider static")
        return StaticGeocoder.from_csv(static_csv)
    raise typer.BadParameter("provider must be one of: census, static")


def _write_report(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        raise typer.BadParameter(f"output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@app.command()
def analyze(
    before_csv: Annotated[Path, typer.Option(exists=True)],
    after_csv: Annotated[Path, typer.Option(exists=True)],
    population_csv: Annotated[Path, typer.Option(exists=True)],
    counties_csv: Annotated[Path, typer.Option(exists=True)],
    candidates_csv: Annotated[Path, typer.Option(exists=True)],
    output_dir: Annotated[Path, typer.Option()] = Path("outputs/analysis"),
    utilization_csv: Annotated[Path | None, typer.Option()] = None,
    before_period: Annotated[str, typer.Option()] = "2025Q4",
    after_period: Annotated[str, typer.Option()] = "2026Q2",
    synthetic_data: Annotated[
        bool, typer.Option(help="Mark generated reports as synthetic demonstration outputs.")
    ] = False,
) -> None:
    """Compare two snapshots and generate analysis outputs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    before = pd.read_csv(before_csv)
    after = pd.read_csv(after_csv)
    population = pd.read_csv(population_csv)
    counties = pd.read_csv(counties_csv)
    candidates = pd.read_csv(candidates_csv)
    events = detect_changes(before, after)
    shocks = compare_county_access(population, before, after, counties)
    interventions = simulate_candidates(population, after, candidates)
    utilization_change = None
    if utilization_csv is not None:
        utilization_change = summarize_utilization_change(
            pd.read_csv(utilization_csv), before_period, after_period
        )
        shocks = shocks.merge(utilization_change, on="county_fips", how="left")
        utilization_change.to_csv(output_dir / "utilization_change.csv", index=False)
    sensitivity = run_sensitivity_analysis(shocks)
    events.to_csv(output_dir / "facility_events.csv", index=False)
    shocks.to_csv(output_dir / "county_shocks.csv", index=False)
    interventions.to_csv(output_dir / "intervention_rankings.csv", index=False)
    sensitivity.to_csv(output_dir / "sensitivity_analysis.csv", index=False)
    brief = generate_policy_brief(
        events,
        shocks,
        interventions,
        utilization_change,
        synthetic_data=synthetic_data,
    )
    (output_dir / "policy_brief.md").write_text(brief)
    (output_dir / "policy_brief.html").write_text(generate_policy_brief_html(brief))
    typer.echo(f"Analysis complete: {output_dir.resolve()}")


if __name__ == "__main__":
    app()
