from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Annotated

import pandas as pd
import typer

from radshock.access import compare_county_access
from radshock.adapters.facilities import (
    FDA_MQSA_PUBLIC_ZIP_URL,
    build_mqsa_review_template,
    finalize_mqsa_review,
    read_fda_mqsa_fixed_width,
)
from radshock.briefs import generate_policy_brief, generate_policy_brief_html
from radshock.changes import detect_changes
from radshock.demo import build_demo
from radshock.intervention import simulate_candidates
from radshock.schemas import validate_facilities
from radshock.snapshots import store_snapshot
from radshock.sources import archive_local_source, fetch_url_source
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
    events.to_csv(output_dir / "facility_events.csv", index=False)
    shocks.to_csv(output_dir / "county_shocks.csv", index=False)
    interventions.to_csv(output_dir / "intervention_rankings.csv", index=False)
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
