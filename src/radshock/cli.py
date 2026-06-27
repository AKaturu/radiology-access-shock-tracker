from __future__ import annotations

import json
import os
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated

import pandas as pd
import typer

from radshock.access import compare_county_access, compare_county_travel_time_access
from radshock.adapters.acs import (
    NC_COUNTY_GAZETTEER_URL_TEMPLATE,
    NC_TRACT_GAZETTEER_URL_TEMPLATE,
    build_nc_county_analysis_context,
    build_nc_tract_analysis_context,
    to_analysis_counties,
    to_county_centroid_population_points,
    to_tract_population_points,
)
from radshock.adapters.facilities import (
    FDA_MQSA_PUBLIC_ZIP_URL,
    build_mqsa_review_template,
    carry_forward_mqsa_review,
    finalize_mqsa_review,
    read_fda_mqsa_fixed_width,
)
from radshock.adapters.hrsa import (
    HRSA_HEALTH_CENTER_SITES_CSV_URL,
    HRSA_HEALTH_CENTER_SITES_DOWNLOAD_PAGE,
    build_hrsa_candidate_review_template,
)
from radshock.briefs import generate_policy_brief, generate_policy_brief_html
from radshock.candidates import build_county_candidate_review_template, finalize_candidate_review
from radshock.changes import detect_changes
from radshock.data_quality import audit_csv_quality, render_quality_markdown
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
from radshock.snapshots import file_sha256, store_snapshot
from radshock.sources import archive_local_source, fetch_url_source
from radshock.travel_times import (
    TRAVEL_TIME_ROUTE_STATUSES,
    build_travel_time_review_template,
    fill_travel_time_review_from_openrouteservice,
    fill_travel_time_review_from_osrm,
    finalize_travel_time_review,
    limit_travel_time_review_origins,
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
    retrieved_on: Annotated[
        str | None,
        typer.Option(help="Archive retrieval date in YYYY-MM-DD format."),
    ] = None,
    force: Annotated[bool, typer.Option(help="Overwrite an existing archived source.")] = False,
) -> None:
    """Download a raw source file into the auditable archive."""
    archived = fetch_url_source(
        url,
        output_dir,
        source_name,
        timeout=timeout,
        retrieved_on=_parse_optional_date(retrieved_on, "retrieved_on"),
        force=force,
    )
    typer.echo(f"Archived source: {archived.resolve()}")
    typer.echo(f"Metadata: {archived.with_suffix(archived.suffix + '.metadata.json').resolve()}")


@app.command("fetch-fda-mqsa")
def fetch_fda_mqsa(
    output_dir: Annotated[Path, typer.Option()] = Path("data/raw"),
    timeout: Annotated[int, typer.Option()] = 60,
    retrieved_on: Annotated[
        str | None,
        typer.Option(help="Archive retrieval date in YYYY-MM-DD format."),
    ] = None,
    force: Annotated[bool, typer.Option(help="Overwrite an existing archived source.")] = False,
) -> None:
    """Download the FDA MQSA weekly public facility ZIP into the source archive."""
    archived = fetch_url_source(
        FDA_MQSA_PUBLIC_ZIP_URL,
        output_dir,
        "fda-mqsa-public",
        timeout=timeout,
        retrieved_on=_parse_optional_date(retrieved_on, "retrieved_on"),
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
    retrieved_on: Annotated[
        str | None,
        typer.Option(help="Archive retrieval date in YYYY-MM-DD format."),
    ] = None,
    force: Annotated[bool, typer.Option(help="Overwrite an existing archived source.")] = False,
) -> None:
    """Archive a manually downloaded source file with checksum metadata."""
    archived = archive_local_source(
        input_path,
        output_dir,
        source_name,
        source_url=source_url,
        retrieved_on=_parse_optional_date(retrieved_on, "retrieved_on"),
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
        "Review required: facility_id, latitude, longitude, active, and review_status must be "
        "completed before snapshot ingestion. annual_capacity is optional and should stay blank "
        "unless a reviewed source supports it."
    )


@app.command("carry-forward-mqsa-review")
def carry_forward_mqsa_review_command(
    input_csv: Annotated[Path, typer.Argument(exists=True, readable=True)],
    previous_review_csv: Annotated[
        Path,
        typer.Option(exists=True, readable=True, help="Prior reviewed MQSA CSV."),
    ],
    output_csv: Annotated[Path, typer.Option()],
    metadata_json: Annotated[
        Path | None,
        typer.Option(help="Optional carry-forward metadata JSON path."),
    ] = None,
    force: Annotated[bool, typer.Option(help="Overwrite an existing output CSV.")] = False,
) -> None:
    """Carry reviewed MQSA fields forward when source_record_hash is unchanged."""
    if output_csv.exists() and not force:
        raise typer.BadParameter(f"output already exists: {output_csv}")
    if metadata_json is not None and metadata_json.exists() and not force:
        raise typer.BadParameter(f"output already exists: {metadata_json}")
    current = pd.read_csv(input_csv, dtype=str, keep_default_na=False)
    previous = pd.read_csv(previous_review_csv, dtype=str, keep_default_na=False)
    result = carry_forward_mqsa_review(current, previous)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_csv, index=False)
    matched_count = int(
        current["source_record_hash"]
        .astype(str)
        .str.strip()
        .isin(set(previous["source_record_hash"].astype(str).str.strip()))
        .sum()
    )
    approved_count = int(
        result["review_status"]
        .astype(str)
        .str.strip()
        .str.lower()
        .isin({"reviewed", "verified", "approved"})
        .sum()
    )
    typer.echo(f"MQSA carry-forward review written: {output_csv.resolve()}")
    typer.echo(
        f"Rows: {len(result)}; matched previous source hashes: {matched_count}; "
        f"approved rows: {approved_count}; still needing review: {len(result) - approved_count}"
    )
    if metadata_json is not None:
        _write_mqsa_carry_forward_metadata(
            metadata_json,
            force=force,
            input_csv=input_csv,
            previous_review_csv=previous_review_csv,
            output_csv=output_csv,
            row_count=len(result),
            matched_count=matched_count,
            approved_count=approved_count,
        )
        typer.echo(f"MQSA carry-forward metadata written: {metadata_json.resolve()}")


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


@app.command("data-quality-report")
def data_quality_report_command(
    input_csv: Annotated[Path, typer.Argument(exists=True, readable=True)],
    dataset_type: Annotated[
        str,
        typer.Option(
            help=(
                "Dataset type: auto, facilities, counties, population_points, "
                "candidates, travel_time_matrix."
            )
        ),
    ] = "auto",
    output_json: Annotated[Path | None, typer.Option()] = None,
    output_md: Annotated[Path | None, typer.Option()] = None,
    force: Annotated[bool, typer.Option(help="Overwrite existing report files.")] = False,
) -> None:
    """Write data-quality JSON/Markdown reports for core RadShock CSV inputs."""
    for path in [output_json, output_md]:
        if path is not None and path.exists() and not force:
            raise typer.BadParameter(f"output already exists: {path}")
    audit = audit_csv_quality(input_csv, dataset_type=dataset_type)
    if output_json is not None:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        typer.echo(f"Data-quality JSON written: {output_json.resolve()}")
    if output_md is not None:
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(render_quality_markdown(audit), encoding="utf-8")
        typer.echo(f"Data-quality Markdown written: {output_md.resolve()}")
    typer.echo(
        f"Data quality: {audit['status']} ({audit['dataset_type']}, "
        f"{audit['row_count']} rows)"
    )


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


@app.command("fetch-census-county-context")
def fetch_census_county_context_command(
    output_csv: Annotated[Path, typer.Option(help="Analysis-ready counties CSV path.")] = Path(
        "data/counties.csv"
    ),
    raw_context_csv: Annotated[
        Path | None,
        typer.Option(help="Optional raw/source-rich Census county context CSV path."),
    ] = Path("data/census_county_context_2024.csv"),
    population_points_csv: Annotated[
        Path | None,
        typer.Option(help="Optional county-centroid population points CSV path."),
    ] = Path("data/population_points.csv"),
    metadata_json: Annotated[
        Path | None,
        typer.Option(help="Optional source metadata JSON path."),
    ] = Path("data/census_county_context_2024.metadata.json"),
    year: Annotated[int, typer.Option(help="ACS/Gazetteer release year.")] = 2024,
    api_key_env: Annotated[
        str,
        typer.Option(help="Environment variable containing the Census API key."),
    ] = "CENSUS_API_KEY",
    timeout: Annotated[int, typer.Option(help="HTTP timeout in seconds.")] = 30,
    force: Annotated[bool, typer.Option(help="Overwrite existing output CSVs.")] = False,
) -> None:
    """Fetch Census county context and write analysis-ready CSV inputs."""
    for path in [output_csv, raw_context_csv, population_points_csv, metadata_json]:
        if path is not None and path.exists() and not force:
            raise typer.BadParameter(f"output already exists: {path}")
    api_key = os.getenv(api_key_env)
    if api_key is None or not api_key.strip():
        raise typer.BadParameter(f"{api_key_env} is not set")
    context = build_nc_county_analysis_context(year=year, api_key=api_key, timeout=timeout)
    counties = to_analysis_counties(context)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    counties.to_csv(output_csv, index=False)
    typer.echo(f"Census county context written: {output_csv.resolve()}")
    eligible_population = int(counties["eligible_population"].sum())
    typer.echo(f"Counties: {len(counties)}; eligible population: {eligible_population}")
    if raw_context_csv is not None:
        raw_context_csv.parent.mkdir(parents=True, exist_ok=True)
        context.to_csv(raw_context_csv, index=False)
        typer.echo(f"Raw Census context written: {raw_context_csv.resolve()}")
    if population_points_csv is not None:
        population_points = to_county_centroid_population_points(context)
        population_points_csv.parent.mkdir(parents=True, exist_ok=True)
        population_points.to_csv(population_points_csv, index=False)
        typer.echo(f"County-centroid population points written: {population_points_csv.resolve()}")
        typer.echo(
            "Population points are county-centroid testing inputs; "
            "use finer reviewed points before publication."
        )
    if metadata_json is not None:
        _write_census_metadata(
            metadata_json,
            force=force,
            year=year,
            geography="county",
            outputs={
                "analysis_counties": output_csv,
                "raw_context": raw_context_csv,
                "population_points": population_points_csv,
            },
            row_counts={
                "counties": len(counties),
                "population_points": len(population_points)
                if population_points_csv is not None
                else 0,
            },
            source_urls=[
                f"https://api.census.gov/data/{year}/acs/acs5",
                NC_COUNTY_GAZETTEER_URL_TEMPLATE.format(year=year),
            ],
            notes=[
                "eligible_population is ACS female population age 50-74.",
                "population_points are county centroids for testing, "
                "not publication-grade routing.",
            ],
        )
        typer.echo(f"Census metadata written: {metadata_json.resolve()}")


@app.command("fetch-census-population-points")
def fetch_census_population_points_command(
    output_csv: Annotated[
        Path,
        typer.Option(help="Tract-centroid population points CSV path."),
    ] = Path("data/population_points_tracts.csv"),
    raw_context_csv: Annotated[
        Path | None,
        typer.Option(help="Optional raw/source-rich Census tract context CSV path."),
    ] = Path("data/census_tract_context_2024.csv"),
    metadata_json: Annotated[
        Path | None,
        typer.Option(help="Optional source metadata JSON path."),
    ] = Path("data/census_tract_context_2024.metadata.json"),
    year: Annotated[int, typer.Option(help="ACS/Gazetteer release year.")] = 2024,
    api_key_env: Annotated[
        str,
        typer.Option(help="Environment variable containing the Census API key."),
    ] = "CENSUS_API_KEY",
    timeout: Annotated[int, typer.Option(help="HTTP timeout in seconds.")] = 30,
    include_zero_weight: Annotated[
        bool,
        typer.Option(help="Keep tract rows with zero eligible-population weight."),
    ] = False,
    force: Annotated[bool, typer.Option(help="Overwrite existing output files.")] = False,
) -> None:
    """Fetch Census tract context and write finer population-point inputs."""
    for path in [output_csv, raw_context_csv, metadata_json]:
        if path is not None and path.exists() and not force:
            raise typer.BadParameter(f"output already exists: {path}")
    api_key = os.getenv(api_key_env)
    if api_key is None or not api_key.strip():
        raise typer.BadParameter(f"{api_key_env} is not set")
    context = build_nc_tract_analysis_context(year=year, api_key=api_key, timeout=timeout)
    population_points = to_tract_population_points(
        context,
        include_zero_weight=include_zero_weight,
    )
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    population_points.to_csv(output_csv, index=False)
    typer.echo(f"Tract population points written: {output_csv.resolve()}")
    eligible_population = int(population_points["weight"].sum())
    typer.echo(f"Points: {len(population_points)}; eligible population: {eligible_population}")
    typer.echo(
        "Population points use Census tract internal points; "
        "route matrices should be regenerated before publication."
    )
    if raw_context_csv is not None:
        raw_context_csv.parent.mkdir(parents=True, exist_ok=True)
        context.to_csv(raw_context_csv, index=False)
        typer.echo(f"Raw Census tract context written: {raw_context_csv.resolve()}")
    if metadata_json is not None:
        _write_census_metadata(
            metadata_json,
            force=force,
            year=year,
            geography="tract",
            outputs={
                "population_points": output_csv,
                "raw_context": raw_context_csv,
            },
            row_counts={
                "tracts": len(context),
                "population_points": len(population_points),
            },
            source_urls=[
                f"https://api.census.gov/data/{year}/acs/acs5",
                NC_TRACT_GAZETTEER_URL_TEMPLATE.format(year=year),
            ],
            notes=[
                "eligible_population is ACS female population age 50-74.",
                "latitude and longitude are Census Gazetteer tract internal points.",
                "tract points are finer than county centroids but remain centroid approximations.",
            ],
        )
        typer.echo(f"Census metadata written: {metadata_json.resolve()}")


@app.command("prepare-travel-time-review")
def prepare_travel_time_review_command(
    population_csv: Annotated[Path, typer.Option(exists=True, readable=True)],
    facilities_csv: Annotated[Path, typer.Option(exists=True, readable=True)],
    output_csv: Annotated[Path, typer.Option()],
    metadata_json: Annotated[
        Path | None,
        typer.Option(help="Optional route-review template metadata JSON path."),
    ] = None,
    max_distance_miles: Annotated[
        float | None,
        typer.Option(help="Optional straight-line prefilter for route pairs."),
    ] = None,
    max_facilities_per_point: Annotated[
        int | None,
        typer.Option(
            help=("Optional nearest-facility cap per population point after distance filtering.")
        ),
    ] = None,
    include_inactive: Annotated[
        bool, typer.Option(help="Include inactive facilities in the routing worklist.")
    ] = False,
    force: Annotated[bool, typer.Option(help="Overwrite an existing output CSV.")] = False,
) -> None:
    """Create a point-to-facility routing worklist for external route review."""
    if output_csv.exists() and not force:
        raise typer.BadParameter(f"output already exists: {output_csv}")
    if metadata_json is not None and metadata_json.exists() and not force:
        raise typer.BadParameter(f"output already exists: {metadata_json}")
    review = build_travel_time_review_template(
        pd.read_csv(population_csv, dtype={"point_id": str, "county_fips": str}),
        pd.read_csv(facilities_csv, dtype={"facility_id": str}),
        active_only=not include_inactive,
        max_distance_miles=max_distance_miles,
        max_facilities_per_point=max_facilities_per_point,
    )
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    review.to_csv(output_csv, index=False)
    typer.echo(f"Travel-time review template written: {output_csv.resolve()}")
    typer.echo(f"Route pairs: {len(review)}")
    if metadata_json is not None:
        _write_travel_time_review_metadata(
            metadata_json,
            force=force,
            output_csv=output_csv,
            population_csv=population_csv,
            facilities_csv=facilities_csv,
            review=review,
            active_only=not include_inactive,
            max_distance_miles=max_distance_miles,
            max_facilities_per_point=max_facilities_per_point,
        )
        typer.echo(f"Travel-time review metadata written: {metadata_json.resolve()}")
    typer.echo(
        "Fill travel_time_minutes, route_status, route provider metadata, and review_status "
        "before finalizing."
    )


@app.command("prepare-candidate-review")
def prepare_candidate_review_command(
    counties_csv: Annotated[Path, typer.Option(exists=True, readable=True)],
    output_csv: Annotated[Path, typer.Option()],
    metadata_json: Annotated[
        Path | None,
        typer.Option(help="Optional candidate-review template metadata JSON path."),
    ] = None,
    force: Annotated[bool, typer.Option(help="Overwrite an existing output CSV.")] = False,
) -> None:
    """Create a candidate-site review CSV from county centroids."""
    if output_csv.exists() and not force:
        raise typer.BadParameter(f"output already exists: {output_csv}")
    if metadata_json is not None and metadata_json.exists() and not force:
        raise typer.BadParameter(f"output already exists: {metadata_json}")
    review = build_county_candidate_review_template(
        pd.read_csv(counties_csv, dtype={"county_fips": str})
    )
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    review.to_csv(output_csv, index=False)
    typer.echo(f"Candidate review template written: {output_csv.resolve()}")
    typer.echo(f"Candidate rows: {len(review)}")
    if metadata_json is not None:
        _write_candidate_review_metadata(
            metadata_json,
            force=force,
            output_csv=output_csv,
            counties_csv=counties_csv,
            review=review,
        )
        typer.echo(f"Candidate review metadata written: {metadata_json.resolve()}")
    typer.echo(
        "County-centroid candidates are placeholders. Review assumptions and set review_status "
        "before running finalize-candidate-review."
    )


@app.command("prepare-hrsa-candidate-review")
def prepare_hrsa_candidate_review_command(
    input_csv: Annotated[Path, typer.Argument(exists=True, readable=True)],
    output_csv: Annotated[Path, typer.Option()],
    metadata_json: Annotated[
        Path | None,
        typer.Option(help="Optional HRSA candidate-review metadata JSON path."),
    ] = None,
    state: Annotated[str, typer.Option(help="Two-letter state filter.")] = "NC",
    include_inactive: Annotated[
        bool,
        typer.Option(help="Include inactive HRSA sites in the review CSV."),
    ] = False,
    include_administrative: Annotated[
        bool,
        typer.Option(help="Include administrative-only HRSA rows in the review CSV."),
    ] = False,
    review_status: Annotated[
        str,
        typer.Option(help="Initial review_status to assign to generated candidate rows."),
    ] = "needs_review",
    force: Annotated[bool, typer.Option(help="Overwrite an existing output CSV.")] = False,
) -> None:
    """Create a candidate-site review CSV from HRSA health-center service sites."""
    if output_csv.exists() and not force:
        raise typer.BadParameter(f"output already exists: {output_csv}")
    if metadata_json is not None and metadata_json.exists() and not force:
        raise typer.BadParameter(f"output already exists: {metadata_json}")
    review = build_hrsa_candidate_review_template(
        pd.read_csv(input_csv, dtype=str, keep_default_na=False),
        state=state,
        active_only=not include_inactive,
        service_delivery_only=not include_administrative,
        review_status=review_status,
    )
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    review.to_csv(output_csv, index=False)
    typer.echo(f"HRSA candidate review template written: {output_csv.resolve()}")
    typer.echo(
        f"Candidate rows: {len(review)}; counties: "
        f"{int(review['county_fips'].nunique()) if len(review) else 0}"
    )
    typer.echo(
        "HRSA sites are real health-center service locations, but remain planning "
        "assumptions here and are not mammography-capability claims."
    )
    if metadata_json is not None:
        _write_hrsa_candidate_review_metadata(
            metadata_json,
            force=force,
            input_csv=input_csv,
            output_csv=output_csv,
            review=review,
            state=state,
            active_only=not include_inactive,
            service_delivery_only=not include_administrative,
        )
        typer.echo(f"HRSA candidate review metadata written: {metadata_json.resolve()}")


@app.command("finalize-candidate-review")
def finalize_candidate_review_command(
    input_csv: Annotated[Path, typer.Argument(exists=True, readable=True)],
    output_csv: Annotated[Path, typer.Option()],
    metadata_json: Annotated[
        Path | None,
        typer.Option(help="Optional finalized candidate metadata JSON path."),
    ] = None,
    force: Annotated[bool, typer.Option(help="Overwrite an existing output CSV.")] = False,
    dry_run: Annotated[bool, typer.Option(help="Validate without writing output.")] = False,
) -> None:
    """Validate reviewed candidate-site assumptions and write analysis-ready candidates."""
    if output_csv.exists() and not force and not dry_run:
        raise typer.BadParameter(f"output already exists: {output_csv}")
    if metadata_json is not None and metadata_json.exists() and not force and not dry_run:
        raise typer.BadParameter(f"output already exists: {metadata_json}")
    candidates = finalize_candidate_review(
        pd.read_csv(input_csv, dtype={"candidate_id": str, "county_fips": str})
    )
    if dry_run:
        typer.echo(f"Candidate review complete: {len(candidates)} candidates")
        return
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    candidates.to_csv(output_csv, index=False)
    typer.echo(f"Analysis-ready candidates written: {output_csv.resolve()}")
    typer.echo(f"Candidate rows: {len(candidates)}")
    if metadata_json is not None:
        _write_finalized_candidate_metadata(
            metadata_json,
            force=force,
            input_csv=input_csv,
            output_csv=output_csv,
            candidates=candidates,
        )
        typer.echo(f"Candidate metadata written: {metadata_json.resolve()}")


@app.command("finalize-travel-time-review")
def finalize_travel_time_review_command(
    input_csv: Annotated[Path, typer.Argument(exists=True, readable=True)],
    output_csv: Annotated[Path, typer.Option()],
    metadata_json: Annotated[
        Path | None,
        typer.Option(help="Optional finalized travel-time metadata JSON path."),
    ] = None,
    force: Annotated[bool, typer.Option(help="Overwrite an existing output CSV.")] = False,
    dry_run: Annotated[bool, typer.Option(help="Validate without writing output.")] = False,
) -> None:
    """Validate reviewed route rows and write a travel-time matrix."""
    if output_csv.exists() and not force and not dry_run:
        raise typer.BadParameter(f"output already exists: {output_csv}")
    if metadata_json is not None and metadata_json.exists() and not force and not dry_run:
        raise typer.BadParameter(f"output already exists: {metadata_json}")
    review = pd.read_csv(
        input_csv,
        dtype={"point_id": str, "facility_id": str},
        keep_default_na=False,
    )
    matrix = finalize_travel_time_review(review)
    if dry_run:
        typer.echo(f"Travel-time review complete: {len(matrix)} routed pairs")
        return
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    matrix.to_csv(output_csv, index=False)
    typer.echo(f"Travel-time matrix written: {output_csv.resolve()}")
    typer.echo(f"Routed pairs: {len(matrix)}")
    if metadata_json is not None:
        _write_finalized_travel_time_metadata(
            metadata_json,
            force=force,
            input_csv=input_csv,
            output_csv=output_csv,
            review=review,
            matrix=matrix,
        )
        typer.echo(f"Travel-time metadata written: {metadata_json.resolve()}")


@app.command("fill-travel-time-review")
def fill_travel_time_review_command(
    input_csv: Annotated[Path, typer.Argument(exists=True, readable=True)],
    output_csv: Annotated[Path, typer.Option()],
    provider: Annotated[str, typer.Option(help="Routing provider to use.")] = "osrm",
    osrm_base_url: Annotated[
        str,
        typer.Option(help="Base URL for an OSRM-compatible routing server."),
    ] = "https://router.project-osrm.org",
    osrm_profile: Annotated[str, typer.Option(help="OSRM routing profile.")] = "driving",
    ors_base_url: Annotated[
        str,
        typer.Option(help="Base URL for the OpenRouteService API."),
    ] = "https://api.openrouteservice.org",
    ors_profile: Annotated[
        str,
        typer.Option(help="OpenRouteService routing profile."),
    ] = "driving-car",
    ors_api_key_env: Annotated[
        str,
        typer.Option(help="Environment variable that contains the OpenRouteService API key."),
    ] = "OPENROUTESERVICE_API_KEY",
    timeout: Annotated[int, typer.Option(help="HTTP timeout in seconds.")] = 60,
    user_agent: Annotated[
        str,
        typer.Option(help="User-Agent sent to the routing provider."),
    ] = "radshock-route-review/0.1",
    request_delay_seconds: Annotated[
        float,
        typer.Option(help="Pause between per-origin routing requests."),
    ] = 0,
    review_status: Annotated[
        str,
        typer.Option(help="Review status to write to routed rows; default keeps rows unapproved."),
    ] = "needs_review",
    only_missing: Annotated[
        bool,
        typer.Option(help="Only fill rows that are not already routed, unreachable, or excluded."),
    ] = False,
    max_origins: Annotated[
        int | None,
        typer.Option(help="Maximum point_id groups to fill in this run."),
    ] = None,
    force: Annotated[bool, typer.Option(help="Overwrite an existing output CSV.")] = False,
) -> None:
    """Fill travel-time review rows with routing provider minutes and provenance."""
    if output_csv.exists() and not force:
        raise typer.BadParameter(f"output already exists: {output_csv}")
    normalized_provider = provider.strip().lower()
    input_frame = pd.read_csv(input_csv, dtype=str, keep_default_na=False)
    fill_frame = input_frame
    if only_missing:
        route_status = input_frame["route_status"].astype(str).str.strip().str.lower()
        fill_frame = input_frame.loc[~route_status.isin(TRAVEL_TIME_ROUTE_STATUSES)].copy()
    fill_frame = limit_travel_time_review_origins(fill_frame, max_origins)
    if normalized_provider == "osrm":
        filled = fill_travel_time_review_from_osrm(
            fill_frame,
            base_url=osrm_base_url,
            profile=osrm_profile,
            timeout=timeout,
            user_agent=user_agent,
            review_status=review_status,
            request_delay_seconds=request_delay_seconds,
        )
    elif normalized_provider in {"openrouteservice", "ors"}:
        api_key = os.getenv(ors_api_key_env)
        if api_key is None or not api_key.strip():
            raise typer.BadParameter(f"{ors_api_key_env} is not set")
        filled = fill_travel_time_review_from_openrouteservice(
            fill_frame,
            api_key=api_key,
            base_url=ors_base_url,
            profile=ors_profile,
            timeout=timeout,
            user_agent=user_agent,
            review_status=review_status,
            request_delay_seconds=request_delay_seconds,
        )
    else:
        raise typer.BadParameter("provider must be one of: osrm, openrouteservice, ors")
    if only_missing:
        result = _merge_filled_route_rows(input_frame, filled)
    else:
        result = filled
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_csv, index=False)
    routed_count = int((result["route_status"] == "routed").sum())
    unreachable_count = int((result["route_status"] == "unreachable").sum())
    error_count = int(result["route_error"].astype(str).str.len().gt(0).sum())
    typer.echo(f"Travel-time review draft written: {output_csv.resolve()}")
    typer.echo(
        f"Rows: {len(result)}; routed: {routed_count}; "
        f"unreachable: {unreachable_count}; errors: {error_count}"
    )
    if review_status == "needs_review":
        typer.echo("Review status remains needs_review; finalize-travel-time-review will block.")


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


def _parse_optional_date(value: str | None, label: str) -> date | None:
    if value is None or not value.strip():
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise typer.BadParameter(f"{label} must use YYYY-MM-DD format") from exc


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


def _merge_filled_route_rows(input_frame: pd.DataFrame, filled: pd.DataFrame) -> pd.DataFrame:
    result = input_frame.copy()
    for column in filled.columns:
        result[column] = result[column].astype("object")
    result.loc[filled.index, filled.columns] = filled.astype("object")
    return result


def _write_census_metadata(
    path: Path,
    *,
    force: bool,
    year: int,
    geography: str,
    outputs: dict[str, Path | None],
    row_counts: dict[str, int],
    source_urls: list[str],
    notes: list[str],
) -> None:
    if path.exists() and not force:
        raise typer.BadParameter(f"output already exists: {path}")
    output_metadata: dict[str, dict[str, str] | None] = {}
    for label, output_path in outputs.items():
        if output_path is None:
            output_metadata[label] = None
            continue
        output_metadata[label] = {
            "path": str(output_path),
            "sha256": file_sha256(output_path),
        }
    metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source_name": "census-acs5-gazetteer",
        "state": "NC",
        "state_fips": "37",
        "year": year,
        "geography": geography,
        "outputs": output_metadata,
        "row_counts": row_counts,
        "source_urls": source_urls,
        "eligible_population_definition": "ACS B01001 female age 50-74 estimate",
        "notes": notes,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_travel_time_review_metadata(
    path: Path,
    *,
    force: bool,
    output_csv: Path,
    population_csv: Path,
    facilities_csv: Path,
    review: pd.DataFrame,
    active_only: bool,
    max_distance_miles: float | None,
    max_facilities_per_point: int | None,
) -> None:
    if path.exists() and not force:
        raise typer.BadParameter(f"output already exists: {path}")
    metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source_name": "radshock-prepare-travel-time-review",
        "output": {
            "path": str(output_csv),
            "sha256": file_sha256(output_csv),
        },
        "inputs": {
            "population_csv": {
                "path": str(population_csv),
                "sha256": file_sha256(population_csv),
            },
            "facilities_csv": {
                "path": str(facilities_csv),
                "sha256": file_sha256(facilities_csv),
            },
        },
        "filters": {
            "active_only": active_only,
            "max_distance_miles": max_distance_miles,
            "max_facilities_per_point": max_facilities_per_point,
        },
        "row_counts": {
            "route_pairs": int(len(review)),
            "population_points": int(review["point_id"].nunique()) if len(review) else 0,
            "facilities": int(review["facility_id"].nunique()) if len(review) else 0,
        },
        "notes": [
            "travel_time_minutes are blank route-review inputs, not route results.",
            "route provider metadata and review_status must be completed before finalization.",
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_mqsa_carry_forward_metadata(
    path: Path,
    *,
    force: bool,
    input_csv: Path,
    previous_review_csv: Path,
    output_csv: Path,
    row_count: int,
    matched_count: int,
    approved_count: int,
) -> None:
    if path.exists() and not force:
        raise typer.BadParameter(f"output already exists: {path}")
    metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source_name": "radshock-carry-forward-mqsa-review",
        "outputs": {
            "review_csv": {
                "path": str(output_csv),
                "sha256": file_sha256(output_csv),
            }
        },
        "inputs": {
            "current_review_template_csv": {
                "path": str(input_csv),
                "sha256": file_sha256(input_csv),
            },
            "previous_review_csv": {
                "path": str(previous_review_csv),
                "sha256": file_sha256(previous_review_csv),
            },
        },
        "row_counts": {
            "rows": row_count,
            "matched_previous_source_hashes": matched_count,
            "approved_rows": approved_count,
            "needs_review_rows": row_count - approved_count,
        },
        "notes": [
            "review fields were carried forward only for exact source_record_hash matches.",
            "changed or new source rows must still be reviewed before finalization.",
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_finalized_travel_time_metadata(
    path: Path,
    *,
    force: bool,
    input_csv: Path,
    output_csv: Path,
    review: pd.DataFrame,
    matrix: pd.DataFrame,
) -> None:
    if path.exists() and not force:
        raise typer.BadParameter(f"output already exists: {path}")
    route_status = (
        review.get("route_status", pd.Series(dtype=str)).astype(str).str.strip().str.lower()
    )
    review_status = (
        review.get("review_status", pd.Series(dtype=str)).astype(str).str.strip().str.lower()
    )
    metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source_name": "radshock-finalize-travel-time-review",
        "outputs": {
            "matrix_csv": {
                "path": str(output_csv),
                "sha256": file_sha256(output_csv),
            }
        },
        "inputs": {
            "review_csv": {
                "path": str(input_csv),
                "sha256": file_sha256(input_csv),
            }
        },
        "row_counts": {
            "route_rows": int(len(review)),
            "routed_rows": int((route_status == "routed").sum()),
            "unreachable_rows": int((route_status == "unreachable").sum()),
            "excluded_rows": int((route_status == "excluded").sum()),
            "approved_review_rows": int(
                review_status.isin({"reviewed", "verified", "approved"}).sum()
            ),
            "population_points": int(review["point_id"].nunique()) if "point_id" in review else 0,
            "facilities": int(review["facility_id"].nunique()) if "facility_id" in review else 0,
            "finalized_matrix_rows": int(len(matrix)),
        },
        "route_metadata": {
            "route_providers": _unique_nonblank_values(review, "route_provider"),
            "route_source_urls": _unique_nonblank_values(review, "route_source_url"),
            "retrieved_at_utc_min": _min_nonblank_value(review, "route_retrieved_at_utc"),
            "retrieved_at_utc_max": _max_nonblank_value(review, "route_retrieved_at_utc"),
        },
        "notes": [
            "finalized matrix includes routed rows only.",
            "provider metadata is retained in the reviewed route CSV referenced here.",
            "traffic assumptions depend on the routing provider and request profile.",
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _unique_nonblank_values(frame: pd.DataFrame, column: str) -> list[str]:
    if column not in frame.columns:
        return []
    values = sorted(
        {
            value
            for value in frame[column].astype(str).str.strip()
            if value and value.lower() != "nan"
        }
    )
    return values


def _min_nonblank_value(frame: pd.DataFrame, column: str) -> str | None:
    values = _unique_nonblank_values(frame, column)
    return min(values) if values else None


def _max_nonblank_value(frame: pd.DataFrame, column: str) -> str | None:
    values = _unique_nonblank_values(frame, column)
    return max(values) if values else None


def _write_candidate_review_metadata(
    path: Path,
    *,
    force: bool,
    output_csv: Path,
    counties_csv: Path,
    review: pd.DataFrame,
) -> None:
    if path.exists() and not force:
        raise typer.BadParameter(f"output already exists: {path}")
    metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source_name": "radshock-prepare-candidate-review",
        "output": {
            "path": str(output_csv),
            "sha256": file_sha256(output_csv),
        },
        "inputs": {
            "counties_csv": {
                "path": str(counties_csv),
                "sha256": file_sha256(counties_csv),
            }
        },
        "row_counts": {
            "candidate_rows": int(len(review)),
            "counties": int(review["county_fips"].nunique()) if len(review) else 0,
        },
        "notes": [
            "county-centroid candidates are placeholder response locations.",
            "review_status must be reviewed, verified, or approved before finalization.",
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_hrsa_candidate_review_metadata(
    path: Path,
    *,
    force: bool,
    input_csv: Path,
    output_csv: Path,
    review: pd.DataFrame,
    state: str,
    active_only: bool,
    service_delivery_only: bool,
) -> None:
    if path.exists() and not force:
        raise typer.BadParameter(f"output already exists: {path}")
    candidate_type_counts = {
        candidate_type: int(count)
        for candidate_type, count in review["candidate_type"].value_counts().sort_index().items()
    }
    metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source_name": "radshock-prepare-hrsa-candidate-review",
        "output": {
            "path": str(output_csv),
            "sha256": file_sha256(output_csv),
        },
        "inputs": {
            "hrsa_health_center_sites_csv": {
                "path": str(input_csv),
                "sha256": file_sha256(input_csv),
            }
        },
        "filters": {
            "state": state.strip().upper(),
            "active_only": active_only,
            "service_delivery_only": service_delivery_only,
        },
        "row_counts": {
            "candidate_rows": int(len(review)),
            "counties": int(review["county_fips"].nunique()) if len(review) else 0,
            "candidate_types": candidate_type_counts,
        },
        "source_urls": [
            HRSA_HEALTH_CENTER_SITES_DOWNLOAD_PAGE,
            HRSA_HEALTH_CENTER_SITES_CSV_URL,
        ],
        "notes": [
            "HRSA rows are real health-center service delivery and look-alike sites.",
            "Candidate rows are planning assumptions, not claims that sites provide mammography.",
            "candidate_type maps HRSA location descriptions to fixed, seasonal, "
            "or mobile assumptions.",
            "review_status must be reviewed, verified, or approved before finalization.",
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_finalized_candidate_metadata(
    path: Path,
    *,
    force: bool,
    input_csv: Path,
    output_csv: Path,
    candidates: pd.DataFrame,
) -> None:
    if path.exists() and not force:
        raise typer.BadParameter(f"output already exists: {path}")
    metadata = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source_name": "radshock-finalize-candidate-review",
        "output": {
            "path": str(output_csv),
            "sha256": file_sha256(output_csv),
        },
        "inputs": {
            "candidate_review_csv": {
                "path": str(input_csv),
                "sha256": file_sha256(input_csv),
            }
        },
        "row_counts": {
            "candidate_rows": int(len(candidates)),
            "counties": int(candidates["county_fips"].nunique()) if len(candidates) else 0,
        },
        "notes": [
            "candidate rows passed finalize-candidate-review approval checks.",
            "candidate locations remain planning assumptions, not endorsed service locations.",
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
    before_snapshot_dir: Annotated[
        Path | None,
        typer.Option(exists=True, file_okay=False, help="Snapshot directory for provenance audit."),
    ] = None,
    after_snapshot_dir: Annotated[
        Path | None,
        typer.Option(exists=True, file_okay=False, help="Snapshot directory for provenance audit."),
    ] = None,
    raw_source_metadata: Annotated[
        Path | None,
        typer.Option(exists=True, readable=True, help="Archived raw-source metadata JSON."),
    ] = None,
    before_period: Annotated[str, typer.Option()] = "2025Q4",
    after_period: Annotated[str, typer.Option()] = "2026Q2",
    synthetic_data: Annotated[
        bool, typer.Option(help="Mark generated reports as synthetic demonstration outputs.")
    ] = False,
    require_travel_time: Annotated[
        bool, typer.Option(help="Block readiness if outputs are distance-only.")
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
    _write_analysis_manifest(
        output_dir,
        before_csv=before_csv,
        after_csv=after_csv,
        population_csv=population_csv,
        counties_csv=counties_csv,
        candidates_csv=candidates_csv,
        utilization_csv=utilization_csv,
        before_period=before_period,
        after_period=after_period,
        synthetic_data=synthetic_data,
    )
    audit = run_readiness_audit(
        output_dir,
        before_snapshot_dir=before_snapshot_dir or _infer_snapshot_dir(before_csv),
        after_snapshot_dir=after_snapshot_dir or _infer_snapshot_dir(after_csv),
        raw_source_metadata=raw_source_metadata,
        require_travel_time=require_travel_time,
    )
    (output_dir / "readiness_audit.json").write_text(audit_to_json(audit), encoding="utf-8")
    (output_dir / "readiness_audit.md").write_text(
        render_readiness_markdown(audit),
        encoding="utf-8",
    )
    blocker_count = sum(check.status == "BLOCKER" for check in audit.checks)
    warning_count = sum(check.status == "WARN" for check in audit.checks)
    typer.echo(f"Analysis complete: {output_dir.resolve()}")
    typer.echo(
        f"Readiness status: {audit.overall_status}; "
        f"blockers: {blocker_count}; warnings: {warning_count}"
    )


def _write_analysis_manifest(
    output_dir: Path,
    before_csv: Path,
    after_csv: Path,
    population_csv: Path,
    counties_csv: Path,
    candidates_csv: Path,
    utilization_csv: Path | None,
    before_period: str,
    after_period: str,
    synthetic_data: bool,
) -> None:
    outputs = {
        "events": "facility_events.csv",
        "county_shocks": "county_shocks.csv",
        "interventions": "intervention_rankings.csv",
        "sensitivity": "sensitivity_analysis.csv",
        "readiness_json": "readiness_audit.json",
        "readiness_md": "readiness_audit.md",
        "brief": "policy_brief.md",
        "brief_html": "policy_brief.html",
    }
    if utilization_csv is not None:
        outputs["utilization"] = "utilization_change.csv"
    manifest = {
        "synthetic_data": synthetic_data,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "command": "analyze",
        "inputs": {
            "before_csv": str(before_csv),
            "after_csv": str(after_csv),
            "population_csv": str(population_csv),
            "counties_csv": str(counties_csv),
            "candidates_csv": str(candidates_csv),
            "utilization_csv": str(utilization_csv) if utilization_csv is not None else None,
        },
        "periods": {
            "before_period": before_period,
            "after_period": after_period,
        },
        "outputs": outputs,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _infer_snapshot_dir(snapshot_csv: Path) -> Path | None:
    if snapshot_csv.name == "facilities.csv" and (snapshot_csv.parent / "metadata.json").exists():
        return snapshot_csv.parent
    return None


if __name__ == "__main__":
    app()
