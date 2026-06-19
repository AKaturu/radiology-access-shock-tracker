from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Annotated

import pandas as pd
import typer

from radshock.access import compare_county_access
from radshock.briefs import generate_policy_brief
from radshock.changes import detect_changes
from radshock.demo import build_demo
from radshock.intervention import simulate_candidates
from radshock.snapshots import store_snapshot
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
) -> None:
    """Validate and store an immutable facility snapshot."""
    try:
        snapshot_date = date.fromisoformat(as_of)
    except ValueError as exc:
        raise typer.BadParameter("as_of must use YYYY-MM-DD format") from exc
    destination = store_snapshot(input_csv, snapshot_date, store_dir, source_name)
    typer.echo(f"Stored snapshot: {destination.resolve()}")


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
    brief = generate_policy_brief(events, shocks, interventions, utilization_change)
    (output_dir / "policy_brief.md").write_text(brief)
    typer.echo(f"Analysis complete: {output_dir.resolve()}")


if __name__ == "__main__":
    app()
