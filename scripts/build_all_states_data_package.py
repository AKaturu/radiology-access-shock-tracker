from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from radshock.adapters.acs import (
    build_county_analysis_context,
    build_tract_analysis_context,
    census_gazetteer_urls,
    fetch_county_gazetteer,
    fetch_tract_gazetteer,
    to_analysis_counties,
    to_county_centroid_population_points,
    to_tract_population_points,
)
from radshock.adapters.facilities import (
    FDA_MQSA_PUBLIC_ZIP_URL,
    build_mqsa_review_template,
    read_fda_mqsa_fixed_width,
)
from radshock.adapters.hrsa import (
    HRSA_HEALTH_CENTER_SITES_CSV_URL,
    HRSA_HEALTH_CENTER_SITES_DOWNLOAD_PAGE,
    build_hrsa_candidate_review_template,
)
from radshock.adapters.places import PLACES_COUNTY_ENDPOINT, fetch_mammography
from radshock.adapters.svi import (
    CDC_ATSDR_SVI_2022_US_COUNTY_CSV_URL,
    CDC_ATSDR_SVI_DOWNLOAD_PAGE,
    read_svi_county_context,
)
from radshock.gates import (
    DEFAULT_RESOLUTIONS_PATH,
    KNOWN_GATES,
    get_active_gate_strings,
    load_resolutions,
)
from radshock.snapshots import file_sha256
from radshock.sources import fetch_url_source
from radshock.states import US_STATE_ABBRS, US_STATE_FIPS, state_abbr_from_fips

ALL_STATES_LABEL = "ALL_STATES"
NBER_FDA_MQSA_PUBLIC_ZIP_URL = "https://data.nber.org/fda/mqsa/public.zip"


def build_all_states_data_package(
    output_dir: Path,
    *,
    year: int,
    force: bool,
    census_api_key: str | None,
    require_acs: bool = False,
    mark_publication_ready: bool = False,
    public_report: Path | None = None,
    resolutions_file: Path | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    review_dir = output_dir / "review"
    context_dir = output_dir / "context"
    summary_dir = output_dir / "summary"
    for directory in [raw_dir, review_dir, context_dir, summary_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    run_date = date.today()
    generated_at = datetime.now(UTC).isoformat()

    fda_archive, mqsa_source_note = _fetch_mqsa_archive(raw_dir, run_date=run_date, force=force)
    mqsa_raw = read_fda_mqsa_fixed_width(fda_archive, state=None)
    mqsa_raw = mqsa_raw[mqsa_raw["source_state"].isin(US_STATE_ABBRS)].reset_index(drop=True)
    mqsa_review = build_mqsa_review_template(mqsa_raw)
    mqsa_review_path = review_dir / "fda_mqsa_all_50_review.csv"
    _write_csv(mqsa_review, mqsa_review_path, force=force)

    hrsa_archive = fetch_url_source(
        HRSA_HEALTH_CENTER_SITES_CSV_URL,
        raw_dir,
        "hrsa-health-center-service-delivery-sites",
        retrieved_on=run_date,
        force=force,
    )
    hrsa_source = pd.read_csv(hrsa_archive, dtype=str, keep_default_na=False)
    hrsa_review = build_hrsa_candidate_review_template(hrsa_source, state="ALL")
    hrsa_review_path = review_dir / "hrsa_candidate_sites_all_50_review.csv"
    _write_csv(hrsa_review, hrsa_review_path, force=force)

    places = fetch_mammography(state="ALL")
    places_path = context_dir / "cdc_places_mammography_all_50.csv"
    _write_csv(places, places_path, force=force)

    county_gazetteer = fetch_county_gazetteer(year=year, state="ALL")
    county_gazetteer_path = context_dir / "census_counties_gazetteer_all_50.csv"
    _write_csv(county_gazetteer, county_gazetteer_path, force=force)

    tract_gazetteer = fetch_tract_gazetteer(year=year, state="ALL")
    tract_gazetteer_path = context_dir / "census_tracts_gazetteer_all_50.csv"
    _write_csv(tract_gazetteer, tract_gazetteer_path, force=force)

    svi_archive = fetch_url_source(
        CDC_ATSDR_SVI_2022_US_COUNTY_CSV_URL,
        raw_dir,
        "cdc-atsdr-svi-2022-us-county",
        retrieved_on=run_date,
        force=force,
    )
    svi_counties = read_svi_county_context(svi_archive, state="ALL")
    svi_counties_path = context_dir / "cdc_atsdr_svi_counties_all_50.csv"
    _write_csv(svi_counties, svi_counties_path, force=force)

    acs_outputs = _maybe_build_acs_outputs(
        context_dir,
        year=year,
        force=force,
        census_api_key=census_api_key,
        require_acs=require_acs,
    )

    state_summary = _build_state_summary(
        mqsa_raw,
        hrsa_review,
        places,
        county_gazetteer,
        tract_gazetteer,
        svi_counties,
        acs_counties=acs_outputs.get("counties_frame"),
        acs_tracts=acs_outputs.get("tracts_frame"),
    )
    state_summary_path = summary_dir / "state_source_summary.csv"
    _write_csv(state_summary, state_summary_path, force=force)
    if require_acs:
        _validate_required_acs_coverage(state_summary)
    gate_resolutions = load_resolutions(resolutions_file)
    if mark_publication_ready:
        active_gates = get_active_gate_strings(gate_resolutions)
        if active_gates:
            raise RuntimeError(
                f"Cannot mark publication ready: {len(active_gates)} gate(s) remain "
                f"unresolved. Resolve all gates first via `radshock resolve-gate` or "
                f"inspect with `radshock gate-status`.\n"
                + "\n".join(f"  - {g}" for g in active_gates)
            )
    state_readiness = _build_state_readiness_audit(state_summary, gate_resolutions)
    state_readiness_path = summary_dir / "state_readiness_gates.csv"
    _write_csv(state_readiness, state_readiness_path, force=force)

    manifest = {
        "generated_at_utc": generated_at,
        "state_scope": ALL_STATES_LABEL,
        "year": year,
        "publication_status": (
            "ready_for_publication" if mark_publication_ready else "not_ready_for_publication"
        ),
        "readiness_gates": _build_package_readiness_gates(state_summary, gate_resolutions),
        "source_notes": {
            "mqsa": mqsa_source_note,
            "acs": acs_outputs["status_note"],
            "state_readiness_audit": (
                "State-by-state gates are emitted for reviewer tracking; publication-ready "
                "builds require each gate to be resolved in the gate resolutions file with "
                "reviewer evidence."
            ),
        },
        "sources": {
            "fda_mqsa_public": FDA_MQSA_PUBLIC_ZIP_URL,
            "nber_fda_mqsa_public_mirror": NBER_FDA_MQSA_PUBLIC_ZIP_URL,
            "hrsa_health_center_sites": HRSA_HEALTH_CENTER_SITES_CSV_URL,
            "hrsa_download_page": HRSA_HEALTH_CENTER_SITES_DOWNLOAD_PAGE,
            "cdc_places_county": PLACES_COUNTY_ENDPOINT,
            "cdc_atsdr_svi_download_page": CDC_ATSDR_SVI_DOWNLOAD_PAGE,
            "cdc_atsdr_svi_2022_us_county": CDC_ATSDR_SVI_2022_US_COUNTY_CSV_URL,
            "census_county_gazetteer": census_gazetteer_urls(
                year=year,
                state="ALL",
                geography="county",
            )[0],
            "census_tract_gazetteer": census_gazetteer_urls(
                year=year,
                state="ALL",
                geography="tract",
            )[0],
            "census_acs5": f"https://api.census.gov/data/{year}/acs/acs5",
        },
        "outputs": _output_metadata(
            {
                "fda_mqsa_archive": fda_archive,
                "fda_mqsa_review": mqsa_review_path,
                "hrsa_archive": hrsa_archive,
                "hrsa_candidate_review": hrsa_review_path,
                "cdc_places_mammography": places_path,
                "cdc_atsdr_svi_archive": svi_archive,
                "cdc_atsdr_svi_counties": svi_counties_path,
                "census_county_gazetteer": county_gazetteer_path,
                "census_tract_gazetteer": tract_gazetteer_path,
                "state_source_summary": state_summary_path,
                "state_readiness_gates": state_readiness_path,
                **acs_outputs["paths"],
            }
        ),
        "row_counts": {
            "mqsa_source_rows": int(len(mqsa_raw)),
            "mqsa_review_rows": int(len(mqsa_review)),
            "hrsa_source_rows": int(len(hrsa_source)),
            "hrsa_candidate_review_rows": int(len(hrsa_review)),
            "places_mammography_rows": int(len(places)),
            "cdc_atsdr_svi_counties": int(len(svi_counties)),
            "census_counties": int(len(county_gazetteer)),
            "census_tracts": int(len(tract_gazetteer)),
            **acs_outputs["row_counts"],
        },
        "state_coverage": _state_coverage_summary(state_summary),
        "state_coverage_gaps": _state_coverage_gaps(state_summary),
    }
    manifest_path = summary_dir / "data_package_manifest.json"
    _write_text(manifest_path, json.dumps(manifest, indent=2, sort_keys=True) + "\n", force=force)

    package_readme = _render_report(
        output_dir=output_dir,
        manifest=manifest,
        state_summary=state_summary,
    )
    readme_path = summary_dir / "README.md"
    _write_text(readme_path, package_readme, force=force)
    if public_report is not None:
        _write_text(public_report, package_readme, force=True)

    return manifest


def _fetch_mqsa_archive(
    raw_dir: Path,
    *,
    run_date: date,
    force: bool,
) -> tuple[Path, dict[str, str]]:
    try:
        archive = fetch_url_source(
            FDA_MQSA_PUBLIC_ZIP_URL,
            raw_dir,
            "fda-mqsa-public",
            retrieved_on=run_date,
            force=force,
        )
        return archive, {
            "selected_source": "fda_mqsa_public",
            "selected_url": FDA_MQSA_PUBLIC_ZIP_URL,
            "primary_status": "downloaded",
            "fallback_status": "not_used",
        }
    except requests.RequestException as exc:
        archive = fetch_url_source(
            NBER_FDA_MQSA_PUBLIC_ZIP_URL,
            raw_dir,
            "nber-fda-mqsa-public-mirror",
            retrieved_on=run_date,
            force=force,
        )
        return archive, {
            "selected_source": "nber_fda_mqsa_public_mirror",
            "selected_url": NBER_FDA_MQSA_PUBLIC_ZIP_URL,
            "primary_status": f"failed: {_summarize_request_exception(exc)}",
            "fallback_status": "downloaded",
        }


def _summarize_request_exception(exc: requests.RequestException) -> str:
    summary = f"{type(exc).__name__}: {exc}"
    return summary if len(summary) <= 300 else summary[:297] + "..."


def _maybe_build_acs_outputs(
    context_dir: Path,
    *,
    year: int,
    force: bool,
    census_api_key: str | None,
    require_acs: bool = False,
) -> dict[str, Any]:
    if census_api_key is None or not census_api_key.strip():
        if require_acs:
            raise RuntimeError(
                "CENSUS_API_KEY is required for a production all-state ACS rebuild. "
                "Set the environment variable or pass --allow-missing-acs for a staging-only run."
            )
        return {
            "status_note": "ACS socioeconomic context skipped because CENSUS_API_KEY is not set.",
            "paths": {},
            "row_counts": {
                "acs_county_context_rows": 0,
                "acs_tract_context_rows": 0,
                "acs_county_population_points": 0,
                "acs_tract_population_points": 0,
            },
            "counties_frame": None,
            "tracts_frame": None,
        }

    county_context = build_county_analysis_context(
        year=year,
        state="ALL",
        api_key=census_api_key,
    )
    analysis_counties = to_analysis_counties(county_context)
    county_points = to_county_centroid_population_points(county_context)
    tract_context = build_tract_analysis_context(
        year=year,
        state="ALL",
        api_key=census_api_key,
    )
    tract_points = to_tract_population_points(tract_context)

    county_context_path = context_dir / "census_acs_county_context_all_50.csv"
    analysis_counties_path = context_dir / "counties_all_50.csv"
    county_points_path = context_dir / "population_points_counties_all_50.csv"
    tract_context_path = context_dir / "census_acs_tract_context_all_50.csv"
    tract_points_path = context_dir / "population_points_tracts_all_50.csv"
    for frame, path in [
        (county_context, county_context_path),
        (analysis_counties, analysis_counties_path),
        (county_points, county_points_path),
        (tract_context, tract_context_path),
        (tract_points, tract_points_path),
    ]:
        _write_csv(frame, path, force=force)

    return {
        "status_note": "ACS socioeconomic context generated from Census ACS 5-year API.",
        "paths": {
            "census_acs_county_context": county_context_path,
            "counties_analysis": analysis_counties_path,
            "population_points_counties": county_points_path,
            "census_acs_tract_context": tract_context_path,
            "population_points_tracts": tract_points_path,
        },
        "row_counts": {
            "acs_county_context_rows": int(len(county_context)),
            "acs_tract_context_rows": int(len(tract_context)),
            "acs_county_population_points": int(len(county_points)),
            "acs_tract_population_points": int(len(tract_points)),
        },
        "counties_frame": county_context,
        "tracts_frame": tract_context,
    }


def _validate_required_acs_coverage(state_summary: pd.DataFrame) -> None:
    missing_counties = _states_without_rows(state_summary, "acs_county_context_rows")
    missing_tracts = _states_without_rows(state_summary, "acs_tract_context_rows")
    if not missing_counties and not missing_tracts:
        return
    raise RuntimeError(
        "ACS county and tract context is required but incomplete; "
        f"missing county context for {_format_state_gap(missing_counties)}; "
        f"missing tract context for {_format_state_gap(missing_tracts)}."
    )


def _build_package_readiness_gates(
    state_summary: pd.DataFrame,
    resolutions: dict[str, Any] | None = None,
) -> list[str]:
    active = list(get_active_gate_strings(resolutions or {}))
    missing_counties = _states_without_rows(state_summary, "acs_county_context_rows")
    missing_tracts = _states_without_rows(state_summary, "acs_tract_context_rows")
    if missing_counties or missing_tracts:
        active.append(
            "ACS county/tract context is incomplete; "
            f"missing county context for {_format_state_gap(missing_counties)}; "
            f"missing tract context for {_format_state_gap(missing_tracts)}."
        )
    return active


def _build_state_readiness_audit(
    state_summary: pd.DataFrame,
    resolutions: dict[str, Any] | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for row in state_summary.itertuples(index=False):
        state = str(row.state)
        fips = str(row.state_fips).zfill(2)
        acs_ready = row.acs_county_context_rows > 0 and row.acs_tract_context_rows > 0
        resolved = _gate_resolved_fips(resolutions or {}, fips)
        mqsa_resolved = "mqsa_review" in resolved
        hrsa_resolved = "hrsa_candidate_review" in resolved
        routing_resolved = "travel_time_matrices" in resolved
        all_ok = mqsa_resolved and hrsa_resolved and routing_resolved and acs_ready
        rows.append(
            {
                "state": state,
                "state_fips": fips,
                "overall_status": "READY" if all_ok else "BLOCKED",
                "mqsa_review_status": "PASS" if mqsa_resolved else "BLOCKER",
                "mqsa_review_detail": (
                    f"{row.mqsa_source_rows} MQSA source row(s); gate resolved."
                    if mqsa_resolved
                    else (
                        f"{row.mqsa_source_rows} MQSA source row(s) require facility-id, "
                        "coordinate, active-status, and review-status approval."
                    )
                ),
                "hrsa_candidate_review_status": "PASS" if hrsa_resolved else "BLOCKER",
                "hrsa_candidate_review_detail": (
                    f"{row.hrsa_candidate_review_rows} HRSA candidate row(s); gate resolved."
                    if hrsa_resolved
                    else (
                        f"{row.hrsa_candidate_review_rows} HRSA candidate row(s) require "
                        "planning-assumption review and approval."
                    )
                ),
                "geocoding_status": "PASS" if mqsa_resolved else "BLOCKER",
                "geocoding_detail": (
                    "MQSA review rows approved as geocoded, snapshot-ready facilities."
                    if mqsa_resolved
                    else (
                        "Non-NC MQSA review rows have not been approved as geocoded, "
                        "snapshot-ready facilities."
                    )
                ),
                "routing_status": "PASS" if routing_resolved else "BLOCKER",
                "routing_detail": (
                    "Travel-time matrices are resolved for this state."
                    if routing_resolved
                    else "All-state travel-time matrices are not present."
                ),
                "acs_status": "PASS" if acs_ready else "BLOCKER",
                "acs_detail": (
                    "ACS county and tract context present for this state."
                    if acs_ready
                    else "ACS county and/or tract context is missing for this state."
                ),
                "publication_status": "PASS" if all_ok else "BLOCKER",
                "publication_detail": (
                    "All gates resolved for this state."
                    if all_ok
                    else (
                        "Do not publish non-NC findings until this state's human review, "
                        "geocoding, routing, and readiness audit pass."
                    )
                ),
            }
        )
    return pd.DataFrame(rows).sort_values("state").reset_index(drop=True)


def _gate_resolved_fips(resolutions: dict[str, Any], fips: str) -> set[str]:
    result: set[str] = set()
    gates_map = resolutions.get("gates", {})
    if not isinstance(gates_map, dict):
        return result
    for gate_name in KNOWN_GATES:
        gate_entry = gates_map.get(gate_name, {})
        states_entry = gate_entry.get("resolved_states", {}) if isinstance(gate_entry, dict) else {}
        if isinstance(states_entry, dict) and fips in states_entry:
            result.add(gate_name)
    return result


def _build_state_summary(
    mqsa_raw: pd.DataFrame,
    hrsa_review: pd.DataFrame,
    places: pd.DataFrame,
    county_gazetteer: pd.DataFrame,
    tract_gazetteer: pd.DataFrame,
    svi_counties: pd.DataFrame,
    *,
    acs_counties: pd.DataFrame | None,
    acs_tracts: pd.DataFrame | None,
) -> pd.DataFrame:
    summary = pd.DataFrame({"state": US_STATE_ABBRS, "state_fips": US_STATE_FIPS})
    summary = _merge_counts(
        summary,
        mqsa_raw,
        state_column="source_state",
        value_name="mqsa_source_rows",
    )
    mobile_hints = (
        mqsa_raw[mqsa_raw["is_mobile_name_hint"]]
        .groupby("source_state")
        .size()
        .rename("mqsa_mobile_name_hints")
        .reset_index()
        .rename(columns={"source_state": "state"})
    )
    summary = summary.merge(mobile_hints, on="state", how="left")
    summary = _merge_fips_counts(
        summary,
        hrsa_review,
        fips_column="county_fips",
        value_name="hrsa_candidate_review_rows",
    )
    summary = _merge_counts(
        summary,
        places,
        state_column="stateabbr",
        value_name="places_mammography_rows",
    )
    places_counties = (
        places.assign(state=places["stateabbr"].astype(str).str.upper())
        .groupby("state")["county_fips"]
        .nunique()
        .rename("places_counties")
        .reset_index()
    )
    summary = summary.merge(places_counties, on="state", how="left")
    summary = _merge_fips_counts(
        summary,
        county_gazetteer,
        fips_column="county_fips",
        value_name="census_counties",
    )
    summary = _merge_fips_counts(
        summary,
        tract_gazetteer,
        fips_column="county_fips",
        value_name="census_tracts",
    )
    summary = _merge_fips_counts(
        summary,
        svi_counties,
        fips_column="county_fips",
        value_name="cdc_atsdr_svi_counties",
    )
    if acs_counties is not None:
        summary = _merge_fips_counts(
            summary,
            acs_counties,
            fips_column="county_fips",
            value_name="acs_county_context_rows",
        )
    else:
        summary["acs_county_context_rows"] = 0
    if acs_tracts is not None:
        summary = _merge_fips_counts(
            summary,
            acs_tracts,
            fips_column="county_fips",
            value_name="acs_tract_context_rows",
        )
    else:
        summary["acs_tract_context_rows"] = 0
    count_columns = [column for column in summary.columns if column not in {"state", "state_fips"}]
    summary[count_columns] = summary[count_columns].fillna(0).astype("int64")
    summary["sources_present"] = (
        (summary["mqsa_source_rows"] > 0).astype(int)
        + (summary["hrsa_candidate_review_rows"] > 0).astype(int)
        + (summary["places_mammography_rows"] > 0).astype(int)
        + (summary["census_counties"] > 0).astype(int)
        + (summary["census_tracts"] > 0).astype(int)
        + (summary["cdc_atsdr_svi_counties"] > 0).astype(int)
    )
    return summary.sort_values("state").reset_index(drop=True)


def _merge_counts(
    summary: pd.DataFrame,
    frame: pd.DataFrame,
    *,
    state_column: str,
    value_name: str,
) -> pd.DataFrame:
    counts = (
        frame.assign(state=frame[state_column].astype(str).str.upper())
        .groupby("state")
        .size()
        .rename(value_name)
        .reset_index()
    )
    return summary.merge(counts, on="state", how="left")


def _merge_fips_counts(
    summary: pd.DataFrame,
    frame: pd.DataFrame,
    *,
    fips_column: str,
    value_name: str,
) -> pd.DataFrame:
    counts = (
        frame.assign(
            state=frame[fips_column]
            .astype(str)
            .str.zfill(5)
            .str.slice(0, 2)
            .apply(state_abbr_from_fips)
        )
        .groupby("state")
        .size()
        .rename(value_name)
        .reset_index()
    )
    return summary.merge(counts, on="state", how="left")


def _state_coverage_summary(state_summary: pd.DataFrame) -> dict[str, int]:
    return {
        "states": int(len(state_summary)),
        "states_with_mqsa_rows": int((state_summary["mqsa_source_rows"] > 0).sum()),
        "states_with_hrsa_candidates": int((state_summary["hrsa_candidate_review_rows"] > 0).sum()),
        "states_with_places_rows": int((state_summary["places_mammography_rows"] > 0).sum()),
        "states_with_census_counties": int((state_summary["census_counties"] > 0).sum()),
        "states_with_census_tracts": int((state_summary["census_tracts"] > 0).sum()),
        "states_with_cdc_atsdr_svi_counties": int(
            (state_summary["cdc_atsdr_svi_counties"] > 0).sum()
        ),
        "states_with_acs_county_context": int((state_summary["acs_county_context_rows"] > 0).sum()),
        "states_with_acs_tract_context": int((state_summary["acs_tract_context_rows"] > 0).sum()),
        "states_with_all_public_no_secret_sources": int(
            (state_summary["sources_present"] == 6).sum()
        ),
    }


def _state_coverage_gaps(state_summary: pd.DataFrame) -> dict[str, list[str]]:
    return {
        "missing_mqsa_rows": _states_without_rows(state_summary, "mqsa_source_rows"),
        "missing_hrsa_candidates": _states_without_rows(
            state_summary, "hrsa_candidate_review_rows"
        ),
        "missing_places_rows": _states_without_rows(state_summary, "places_mammography_rows"),
        "missing_census_counties": _states_without_rows(state_summary, "census_counties"),
        "missing_census_tracts": _states_without_rows(state_summary, "census_tracts"),
        "missing_cdc_atsdr_svi_counties": _states_without_rows(
            state_summary, "cdc_atsdr_svi_counties"
        ),
        "missing_acs_county_context": _states_without_rows(
            state_summary, "acs_county_context_rows"
        ),
        "missing_acs_tract_context": _states_without_rows(state_summary, "acs_tract_context_rows"),
        "missing_any_public_no_secret_source": state_summary.loc[
            state_summary["sources_present"] < 6, "state"
        ]
        .astype(str)
        .tolist(),
    }


def _states_without_rows(state_summary: pd.DataFrame, column: str) -> list[str]:
    return state_summary.loc[state_summary[column] <= 0, "state"].astype(str).tolist()


def _render_report(
    *,
    output_dir: Path,
    manifest: dict[str, Any],
    state_summary: pd.DataFrame,
) -> str:
    row_counts = manifest["row_counts"]
    coverage = manifest["state_coverage"]
    top_mqsa = state_summary.nlargest(8, "mqsa_source_rows")[
        ["state", "mqsa_source_rows", "hrsa_candidate_review_rows", "places_counties"]
    ]
    top_lines = "\n".join(
        f"| {row.state} | {row.mqsa_source_rows} | "
        f"{row.hrsa_candidate_review_rows} | {row.places_counties} |"
        for row in top_mqsa.itertuples(index=False)
    )
    gates = "\n".join(f"- {gate}" for gate in manifest["readiness_gates"]) or "- None."
    all_public_sources = coverage["states_with_all_public_no_secret_sources"]
    coverage_gaps = _render_coverage_gaps(manifest["state_coverage_gaps"])
    return f"""# All-States Data Package

Generated: `{manifest["generated_at_utc"]}`

Package directory: `{output_dir}`

## What Was Gathered

- FDA MQSA national source rows: `{row_counts["mqsa_source_rows"]}`
- FDA MQSA review-template rows: `{row_counts["mqsa_review_rows"]}`
- HRSA source rows: `{row_counts["hrsa_source_rows"]}`
- HRSA candidate review-template rows: `{row_counts["hrsa_candidate_review_rows"]}`
- CDC PLACES mammography rows: `{row_counts["places_mammography_rows"]}`
- CDC/ATSDR SVI county rows: `{row_counts["cdc_atsdr_svi_counties"]}`
- Census county Gazetteer rows: `{row_counts["census_counties"]}`
- Census tract Gazetteer rows: `{row_counts["census_tracts"]}`
- ACS county context rows: `{row_counts["acs_county_context_rows"]}`
- ACS tract context rows: `{row_counts["acs_tract_context_rows"]}`

## Coverage

- States in scope: `{coverage["states"]}`
- States with MQSA rows: `{coverage["states_with_mqsa_rows"]}`
- States with HRSA candidate rows: `{coverage["states_with_hrsa_candidates"]}`
- States with CDC PLACES mammography rows: `{coverage["states_with_places_rows"]}`
- States with CDC/ATSDR SVI county rows: `{coverage["states_with_cdc_atsdr_svi_counties"]}`
- States with Census counties: `{coverage["states_with_census_counties"]}`
- States with Census tracts: `{coverage["states_with_census_tracts"]}`
- States with all public no-secret sources present: `{all_public_sources}`
- States with ACS county context: `{coverage["states_with_acs_county_context"]}`
- States with ACS tract context: `{coverage["states_with_acs_tract_context"]}`

## Coverage Gaps

{coverage_gaps}

## Highest MQSA Row Counts

| State | MQSA rows | HRSA candidates | PLACES counties |
|---|---:|---:|---:|
{top_lines}

## Readiness Gates

{gates}

## Key Files

- `review/fda_mqsa_all_50_review.csv`
- `review/hrsa_candidate_sites_all_50_review.csv`
- `context/cdc_places_mammography_all_50.csv`
- `context/cdc_atsdr_svi_counties_all_50.csv`
- `context/census_counties_gazetteer_all_50.csv`
- `context/census_tracts_gazetteer_all_50.csv`
- `summary/state_source_summary.csv`
- `summary/state_readiness_gates.csv`
- `summary/data_package_manifest.json`
"""


def _render_coverage_gaps(gaps: dict[str, list[str]]) -> str:
    public_gap_keys = [
        "missing_mqsa_rows",
        "missing_hrsa_candidates",
        "missing_places_rows",
        "missing_census_counties",
        "missing_census_tracts",
        "missing_cdc_atsdr_svi_counties",
        "missing_any_public_no_secret_source",
    ]
    lines: list[str] = []
    if not any(gaps[key] for key in public_gap_keys):
        lines.append("- Public no-secret source coverage: no state gaps detected.")
    else:
        for key in public_gap_keys:
            if gaps[key]:
                lines.append(f"- {key}: {_format_state_gap(gaps[key])}")
    for key in ["missing_acs_county_context", "missing_acs_tract_context"]:
        if gaps[key]:
            lines.append(f"- {key}: {_format_state_gap(gaps[key])}")
    return "\n".join(lines)


def _format_state_gap(states: list[str]) -> str:
    if not states:
        return "none"
    preview = ", ".join(states[:12])
    remaining = len(states) - 12
    if remaining > 0:
        return f"{preview}, and {remaining} more"
    return preview


def _output_metadata(paths: dict[str, Path]) -> dict[str, dict[str, str | int]]:
    metadata: dict[str, dict[str, str | int]] = {}
    for label, path in paths.items():
        metadata[label] = {
            "path": str(path),
            "sha256": file_sha256(path),
            "size_bytes": path.stat().st_size,
        }
    return metadata


def _write_csv(frame: pd.DataFrame, path: Path, *, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def _write_text(path: Path, content: str, *, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a 51-jurisdiction public-source staging package."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("work/all-states") / date.today().isoformat(),
    )
    parser.add_argument("--year", type=int, default=2024)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--census-api-key-env",
        default="CENSUS_API_KEY",
        help="Environment variable containing a Census API key for optional ACS pulls.",
    )
    parser.add_argument(
        "--allow-missing-acs",
        action="store_true",
        help=(
            "Build a staging-only package when the Census API key is unavailable. "
            "By default, ACS county and tract context is required."
        ),
    )
    parser.add_argument(
        "--public-report",
        type=Path,
        default=None,
        help="Optional extra Markdown report path for user-facing output.",
    )
    parser.add_argument(
        "--mark-publication-ready",
        action="store_true",
        help=(
            "Set publication_status to ready_for_publication in the manifest. "
            "Use only after all-state human review, geocoding, routing, and "
            "readiness gates are resolved."
        ),
    )
    parser.add_argument(
        "--resolutions-file",
        type=Path,
        default=None,
        help=(f"Path to gate resolutions tracking file. Defaults to {DEFAULT_RESOLUTIONS_PATH}."),
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    census_api_key = os.getenv(args.census_api_key_env)
    manifest = build_all_states_data_package(
        args.output_dir,
        year=args.year,
        force=args.force,
        census_api_key=census_api_key,
        require_acs=not args.allow_missing_acs,
        mark_publication_ready=args.mark_publication_ready,
        public_report=args.public_report,
        resolutions_file=args.resolutions_file,
    )
    print(json.dumps({"output_dir": str(args.output_dir), **manifest["row_counts"]}, indent=2))


if __name__ == "__main__":
    main()
