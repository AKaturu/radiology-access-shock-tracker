from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from radshock.access import compare_county_access
from radshock.briefs import generate_policy_brief, generate_policy_brief_html
from radshock.changes import detect_changes
from radshock.intervention import simulate_candidates
from radshock.readiness import audit_to_json, render_readiness_markdown, run_readiness_audit
from radshock.sensitivity import run_sensitivity_analysis
from radshock.snapshots import file_sha256
from radshock.utilization import summarize_utilization_change


def build_demo(output_dir: Path) -> dict[str, Path]:
    """Create synthetic NC-like data and run the entire surveillance pipeline."""
    output_dir.mkdir(parents=True, exist_ok=True)
    inputs = output_dir / "inputs"
    snapshots = output_dir / "snapshots"
    analysis = output_dir / "analysis"
    briefs = output_dir / "briefs"
    for directory in [inputs, snapshots, analysis, briefs]:
        directory.mkdir(parents=True, exist_ok=True)

    counties = _counties()
    population = _population_points(counties)
    before = _before_facilities()
    after = _after_facilities()
    candidates = _candidates(counties)
    utilization = _utilization(counties)

    counties.to_csv(inputs / "counties.csv", index=False)
    population.to_csv(inputs / "population_points.csv", index=False)
    candidates.to_csv(inputs / "candidate_sites.csv", index=False)
    utilization.to_csv(inputs / "utilization.csv", index=False)
    _write_snapshot(before, snapshots / "2026-01-01", "synthetic-demo")
    _write_snapshot(after, snapshots / "2026-04-01", "synthetic-demo")

    events = detect_changes(before, after)
    shocks = compare_county_access(population, before, after, counties)
    utilization_change = summarize_utilization_change(utilization, "2025Q4", "2026Q2")
    shocks = shocks.merge(utilization_change, on="county_fips", how="left")
    interventions = simulate_candidates(population, after, candidates)
    sensitivity = run_sensitivity_analysis(shocks)

    events.to_csv(analysis / "facility_events.csv", index=False)
    shocks.to_csv(analysis / "county_shocks.csv", index=False)
    interventions.to_csv(analysis / "intervention_rankings.csv", index=False)
    utilization_change.to_csv(analysis / "utilization_change.csv", index=False)
    sensitivity.to_csv(analysis / "sensitivity_analysis.csv", index=False)

    brief = generate_policy_brief(
        events,
        shocks,
        interventions,
        utilization_change,
        title="Demonstration Radiology Access Shock Brief",
        as_of=date(2026, 4, 1),
        synthetic_data=True,
    )
    (briefs / "policy_brief.md").write_text(brief)
    (briefs / "policy_brief.html").write_text(generate_policy_brief_html(brief))
    manifest = {
        "synthetic_data": True,
        "before_snapshot": "2026-01-01",
        "after_snapshot": "2026-04-01",
        "outputs": {
            "events": "analysis/facility_events.csv",
            "county_shocks": "analysis/county_shocks.csv",
            "interventions": "analysis/intervention_rankings.csv",
            "utilization": "analysis/utilization_change.csv",
            "sensitivity": "analysis/sensitivity_analysis.csv",
            "brief": "briefs/policy_brief.md",
            "brief_html": "briefs/policy_brief.html",
        },
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    audit = run_readiness_audit(
        analysis,
        before_snapshot_dir=snapshots / "2026-01-01",
        after_snapshot_dir=snapshots / "2026-04-01",
    )
    (analysis / "readiness_audit.json").write_text(audit_to_json(audit))
    (analysis / "readiness_audit.md").write_text(render_readiness_markdown(audit))
    return {
        "events": analysis / "facility_events.csv",
        "shocks": analysis / "county_shocks.csv",
        "interventions": analysis / "intervention_rankings.csv",
        "sensitivity": analysis / "sensitivity_analysis.csv",
        "readiness_json": analysis / "readiness_audit.json",
        "readiness_md": analysis / "readiness_audit.md",
        "brief": briefs / "policy_brief.md",
        "brief_html": briefs / "policy_brief.html",
    }


def _write_snapshot(frame: pd.DataFrame, directory: Path, source: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "facilities.csv"
    frame.to_csv(path, index=False)
    metadata = {
        "as_of": directory.name,
        "source_name": source,
        "synthetic_data": True,
        "record_count": len(frame),
        "sha256": file_sha256(path),
    }
    (directory / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")


def _counties() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["37001", "Northfield County", "NC", 36.10, -78.20, 26000, 12.0, 0.25, 0.35],
            ["37003", "Pine River County", "NC", 35.75, -79.00, 33000, 14.0, 0.35, 0.40],
            ["37005", "Sand Ridge County", "NC", 35.05, -79.30, 28000, 21.0, 0.70, 0.62],
            ["37007", "Cape Meadow County", "NC", 35.20, -77.20, 24000, 24.0, 0.78, 0.66],
            ["37009", "Blue Summit County", "NC", 35.60, -82.55, 30000, 15.0, 0.55, 0.48],
            ["37011", "Roanoke Plains County", "NC", 36.15, -77.45, 21000, 25.0, 0.86, 0.72],
            ["37013", "Cedar Coast County", "NC", 35.55, -76.35, 15000, 27.0, 0.95, 0.76],
            ["37015", "Central Oak County", "NC", 35.85, -78.65, 52000, 10.0, 0.12, 0.30],
        ],
        columns=[
            "county_fips",
            "county_name",
            "state",
            "centroid_lat",
            "centroid_lon",
            "eligible_population",
            "poverty_pct",
            "rurality_index",
            "high_risk_index",
        ],
    )


def _population_points(counties: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(20260619)
    rows: list[dict[str, object]] = []
    for county in counties.itertuples(index=False):
        shares = rng.dirichlet(np.ones(6))
        for index, share in enumerate(shares, start=1):
            rows.append(
                {
                    "point_id": f"{county.county_fips}-P{index}",
                    "county_fips": county.county_fips,
                    "latitude": county.centroid_lat + rng.normal(0, 0.12),
                    "longitude": county.centroid_lon + rng.normal(0, 0.14),
                    "weight": round(county.eligible_population * share, 2),
                }
            )
    return pd.DataFrame(rows)


def _before_facilities() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["F001", "Central Breast Center", 35.86, -78.66, 16000, True],
            ["F002", "Cape Regional Mammography", 35.18, -77.10, 9000, True],
            ["F003", "Blue Summit Imaging", 35.59, -82.54, 11000, True],
            ["F004", "Sandhills Screening Center", 35.06, -79.20, 8500, True],
            ["F005", "Roanoke Women's Imaging", 36.12, -77.42, 7000, True],
        ],
        columns=[
            "facility_id",
            "facility_name",
            "latitude",
            "longitude",
            "annual_capacity",
            "active",
        ],
    )


def _after_facilities() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["F001", "Central Breast Center", 35.82, -78.56, 16000, True],
            ["F003", "Blue Summit Imaging", 35.59, -82.54, 5500, True],
            ["F004", "Sandhills Screening Center", 35.06, -79.20, 8500, True],
            ["F005", "Roanoke Women's Imaging", 36.12, -77.42, 7000, True],
            ["F006", "Pine River Mobile Mammography", 35.69, -78.95, 4500, True],
        ],
        columns=[
            "facility_id",
            "facility_name",
            "latitude",
            "longitude",
            "annual_capacity",
            "active",
        ],
    )


def _candidates(counties: pd.DataFrame) -> pd.DataFrame:
    result = counties[["county_fips", "county_name", "centroid_lat", "centroid_lon"]].copy()
    result["candidate_id"] = "C-" + result["county_fips"]
    result["candidate_name"] = result["county_name"] + " Mobile Stop"
    return result.rename(columns={"centroid_lat": "latitude", "centroid_lon": "longitude"})[
        ["candidate_id", "candidate_name", "county_fips", "latitude", "longitude"]
    ]


def _utilization(counties: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(41)
    rows: list[dict[str, object]] = []
    declining = {"37007": -0.18, "37013": -0.12, "37009": -0.06}
    for county in counties.itertuples(index=False):
        base_rate = 105 - 60 * county.rurality_index + rng.normal(0, 3)
        beneficiaries = max(2500, round(county.eligible_population * 0.32))
        periods = [
            ("2025Q4", 1.0),
            ("2026Q2", 1.0 + declining.get(county.county_fips, 0.01)),
        ]
        for period, multiplier in periods:
            services = max(0, round(base_rate * multiplier * beneficiaries / 1000))
            rows.append(
                {
                    "period": period,
                    "county_fips": county.county_fips,
                    "screening_services": services,
                    "eligible_beneficiaries": beneficiaries,
                }
            )
    return pd.DataFrame(rows)
