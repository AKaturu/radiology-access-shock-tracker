from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from radshock.readiness import find_manifest_path

st.set_page_config(page_title="Radiology Access Shock Tracker", layout="wide")
st.title("Radiology Access Shock Tracker")
st.caption("Surveillance for changes in mammography access and potential community impact")

default_analysis_dir = os.environ.get("RADSHOCK_ANALYSIS_DIR", "outputs/demo/analysis")
analysis_dir = Path(st.sidebar.text_input("Analysis directory", value=default_analysis_dir))
manifest_path = find_manifest_path(analysis_dir)
brief_candidates = [
    analysis_dir.parent / "briefs" / "policy_brief.md",
    analysis_dir / "policy_brief.md",
]
html_brief_candidates = [
    analysis_dir.parent / "briefs" / "policy_brief.html",
    analysis_dir / "policy_brief.html",
]
required = {
    "events": analysis_dir / "facility_events.csv",
    "shocks": analysis_dir / "county_shocks.csv",
    "interventions": analysis_dir / "intervention_rankings.csv",
}
utilization_path = analysis_dir / "utilization_change.csv"
sensitivity_path = analysis_dir / "sensitivity_analysis.csv"
sensitivity_md_path = analysis_dir / "sensitivity_analysis.md"
sensitivity_html_path = analysis_dir / "sensitivity_analysis.html"
readiness_json_path = analysis_dir / "readiness_audit.json"
readiness_md_path = analysis_dir / "readiness_audit.md"
data_quality_path = analysis_dir / "data_quality.csv"
geocoder_confidence_path = analysis_dir / "geocoder_confidence.csv"
identifier_crosswalk_path = analysis_dir / "identifier_crosswalk.csv"
route_uncertainty_path = analysis_dir / "route_uncertainty.csv"
missing = [str(path) for path in required.values() if not path.exists()]
if missing:
    st.warning("Run `radshock demo` first. Missing: " + ", ".join(missing))
    st.stop()

events = pd.read_csv(required["events"])
shocks = pd.read_csv(required["shocks"], dtype={"county_fips": str})
interventions = pd.read_csv(required["interventions"], dtype={"county_fips": str})
utilization = (
    pd.read_csv(utilization_path, dtype={"county_fips": str})
    if utilization_path.exists()
    else pd.DataFrame()
)
sensitivity = (
    pd.read_csv(sensitivity_path, dtype={"county_fips": str})
    if sensitivity_path.exists()
    else pd.DataFrame()
)
data_quality = pd.read_csv(data_quality_path) if data_quality_path.exists() else pd.DataFrame()
geocoder_confidence = (
    pd.read_csv(geocoder_confidence_path, dtype=str)
    if geocoder_confidence_path.exists()
    else pd.DataFrame()
)
identifier_crosswalk = (
    pd.read_csv(identifier_crosswalk_path, dtype=str)
    if identifier_crosswalk_path.exists()
    else pd.DataFrame()
)
route_uncertainty = (
    pd.read_csv(route_uncertainty_path) if route_uncertainty_path.exists() else pd.DataFrame()
)
readiness_audit = {}
readiness_error = ""
if readiness_json_path.exists():
    try:
        readiness_audit = json.loads(readiness_json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        readiness_error = f"Readiness audit JSON could not be parsed: {exc}"
manifest = (
    json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path is not None else {}
)


def available_columns(columns: list[str], frame: pd.DataFrame) -> list[str]:
    return [column for column in columns if column in frame.columns]


if bool(manifest.get("synthetic_data")):
    st.warning(
        "Synthetic demonstration data are loaded. Do not interpret these outputs as real "
        "North Carolina findings."
    )

critical = int(shocks["alert_level"].isin(["WARNING", "CRITICAL"]).sum())
col1, col2, col3, col4 = st.columns(4)
col1.metric("Facility events", len(events))
col2.metric("Counties flagged", critical)
col3.metric("Highest shock score", f"{shocks['shock_score'].max():.1f}")
col4.metric("Best intervention score", f"{interventions['intervention_score'].max():.1f}")

(
    overview,
    event_tab,
    county_tab,
    intervention_tab,
    utilization_tab,
    sensitivity_tab,
    quality_tab,
    readiness_tab,
    methods_tab,
) = st.tabs(
    [
        "Overview",
        "Facility events",
        "County shocks",
        "Interventions",
        "Utilization",
        "Sensitivity",
        "Data quality",
        "Readiness",
        "Methods",
    ]
)

with overview:
    st.subheader("County shock surveillance")
    hover_data: dict[str, str | bool] = {"shock_score": ":.1f"}
    for column in [
        "mean_distance_delta",
        "p90_distance_delta",
        "mean_travel_time_delta",
        "p90_travel_time_delta",
    ]:
        if column in shocks.columns:
            hover_data[column] = ":+.1f"
    for column in [
        "population_newly_over_30_miles",
        "population_newly_over_30_minutes",
        "population_newly_over_45_minutes",
        "population_nearest_facility_changed",
    ]:
        if column in shocks.columns:
            hover_data[column] = ":,.0f"
    for column in ["centroid_lat", "centroid_lon", "plot_size"]:
        hover_data[column] = False
    map_shocks = shocks.copy()
    map_shocks["plot_size"] = map_shocks["shock_score"].clip(lower=4)
    fig = px.scatter(
        map_shocks,
        x="centroid_lon",
        y="centroid_lat",
        size="plot_size",
        color="alert_level",
        hover_name="county_name",
        hover_data=hover_data,
        height=560,
    )
    fig.update_traces(marker={"line": {"color": "white", "width": 1.25}})
    fig.update_layout(
        xaxis_title="Longitude",
        yaxis_title="Latitude",
        plot_bgcolor="#f8fafc",
        yaxis={"scaleanchor": "x", "scaleratio": 1},
        margin={"l": 0, "r": 0, "t": 20, "b": 0},
    )
    st.plotly_chart(fig, width="stretch")
    st.info("Facility events are surveillance signals requiring source verification.")

with event_tab:
    if "requires_verification" in events.columns:
        verification_options = ["ALL", "requires verification", "verified"]
        selected_verification = st.selectbox("Verification status", verification_options)
        if selected_verification == "requires verification":
            event_display = events[events["requires_verification"].astype(bool)]
        elif selected_verification == "verified":
            event_display = events[~events["requires_verification"].astype(bool)]
        else:
            event_display = events
    else:
        event_display = events
    st.dataframe(event_display, width="stretch", hide_index=True)
    st.download_button(
        "Download facility events",
        event_display.to_csv(index=False),
        file_name="facility_events.csv",
        mime="text/csv",
    )

with county_tab:
    alert_options = ["ALL"] + sorted(shocks["alert_level"].dropna().unique().tolist())
    selected_alert = st.selectbox("Alert level", alert_options)
    filtered_shocks = (
        shocks if selected_alert == "ALL" else shocks[shocks["alert_level"] == selected_alert]
    )
    display_columns = [
        "county_name",
        "alert_level",
        "shock_score",
        "deterioration_component",
        "vulnerability_component",
        "shock_mean_distance_component",
        "shock_p90_distance_component",
        "shock_mean_travel_time_component",
        "shock_p90_travel_time_component",
        "shock_threshold_component",
        "mean_distance_miles_before",
        "mean_distance_miles_after",
        "mean_distance_delta",
        "p90_distance_delta",
        "mean_travel_time_minutes_before",
        "mean_travel_time_minutes_after",
        "mean_travel_time_delta",
        "p90_travel_time_minutes_before",
        "p90_travel_time_minutes_after",
        "p90_travel_time_delta",
        "pct_over_45_minutes_before",
        "pct_over_45_minutes_after",
        "pct_over_threshold_delta",
        "travel_time_coverage_before",
        "travel_time_coverage_after",
        "population_newly_over_30_miles",
        "population_newly_over_30_minutes",
        "population_newly_over_45_miles",
        "population_newly_over_45_minutes",
        "population_newly_over_60_miles",
        "population_newly_over_60_minutes",
        "population_nearest_facility_changed",
        "utilization_delta_per_1000",
    ]
    display_columns = available_columns(display_columns, filtered_shocks)
    st.dataframe(filtered_shocks[display_columns], width="stretch", hide_index=True)
    st.download_button(
        "Download county shocks",
        filtered_shocks.to_csv(index=False),
        file_name="county_shocks.csv",
        mime="text/csv",
    )

with intervention_tab:
    fig = px.bar(
        interventions.head(8),
        x="intervention_score",
        y="candidate_name",
        orientation="h",
        hover_data=["person_miles_reduced", "population_brought_within_threshold"],
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, width="stretch")
    st.dataframe(interventions, width="stretch", hide_index=True)
    st.download_button(
        "Download intervention rankings",
        interventions.to_csv(index=False),
        file_name="intervention_rankings.csv",
        mime="text/csv",
    )

with utilization_tab:
    if utilization.empty:
        st.info("No utilization signal output found.")
    else:
        st.dataframe(utilization, width="stretch", hide_index=True)
        st.download_button(
            "Download utilization signals",
            utilization.to_csv(index=False),
            file_name="utilization_change.csv",
            mime="text/csv",
        )

with sensitivity_tab:
    if sensitivity.empty:
        st.info("No sensitivity analysis output found.")
    else:
        scenario_options = sensitivity["scenario_id"].dropna().unique().tolist()
        selected_scenario = st.selectbox("Scenario", scenario_options)
        scenario_rows = sensitivity[sensitivity["scenario_id"] == selected_scenario].copy()
        display_columns = [
            "scenario_name",
            "county_name",
            "baseline_shock_score",
            "sensitivity_shock_score",
            "score_delta_from_baseline",
            "baseline_alert_level",
            "sensitivity_alert_level",
            "baseline_rank",
            "sensitivity_rank",
            "rank_delta_from_baseline",
        ]
        display_columns = available_columns(display_columns, scenario_rows)
        st.dataframe(scenario_rows[display_columns], width="stretch", hide_index=True)
        st.download_button(
            "Download sensitivity analysis",
            sensitivity.to_csv(index=False),
            file_name="sensitivity_analysis.csv",
            mime="text/csv",
        )
        if sensitivity_md_path.exists():
            st.download_button(
                "Download sensitivity review report",
                sensitivity_md_path.read_text(encoding="utf-8"),
                file_name="sensitivity_analysis.md",
                mime="text/markdown",
            )
        if sensitivity_html_path.exists():
            st.download_button(
                "Download sensitivity HTML report",
                sensitivity_html_path.read_text(encoding="utf-8"),
                file_name="sensitivity_analysis.html",
                mime="text/html",
            )

with quality_tab:
    if data_quality.empty and geocoder_confidence.empty and route_uncertainty.empty:
        st.info("No data-quality outputs found.")
    else:
        if not data_quality.empty:
            st.subheader("Data-quality checks")
            st.dataframe(data_quality, width="stretch", hide_index=True)
            st.download_button(
                "Download data-quality checks",
                data_quality.to_csv(index=False),
                file_name="data_quality.csv",
                mime="text/csv",
            )
        if not geocoder_confidence.empty:
            st.subheader("Geocoder confidence")
            st.dataframe(geocoder_confidence, width="stretch", hide_index=True)
            st.download_button(
                "Download geocoder confidence",
                geocoder_confidence.to_csv(index=False),
                file_name="geocoder_confidence.csv",
                mime="text/csv",
            )
        if not identifier_crosswalk.empty:
            st.subheader("Identifier crosswalk")
            st.dataframe(identifier_crosswalk, width="stretch", hide_index=True)
            st.download_button(
                "Download identifier crosswalk",
                identifier_crosswalk.to_csv(index=False),
                file_name="identifier_crosswalk.csv",
                mime="text/csv",
            )
        if not route_uncertainty.empty:
            st.subheader("Route uncertainty")
            st.dataframe(route_uncertainty, width="stretch", hide_index=True)
            st.download_button(
                "Download route uncertainty",
                route_uncertainty.to_csv(index=False),
                file_name="route_uncertainty.csv",
                mime="text/csv",
            )

with readiness_tab:
    if readiness_error:
        st.error(readiness_error)
    elif not readiness_audit:
        st.info("No production readiness audit found.")
    else:
        overall_status = str(readiness_audit.get("overall_status", "UNKNOWN"))
        checks = pd.DataFrame(readiness_audit.get("checks", []))
        blocker_count = (
            int(checks["status"].eq("BLOCKER").sum()) if "status" in checks.columns else 0
        )
        warning_count = int(checks["status"].eq("WARN").sum()) if "status" in checks.columns else 0
        pass_count = int(checks["status"].eq("PASS").sum()) if "status" in checks.columns else 0
        status_col, blocker_col, warning_col, pass_col = st.columns(4)
        status_col.metric("Readiness status", overall_status)
        blocker_col.metric("Blockers", blocker_count)
        warning_col.metric("Warnings", warning_count)
        pass_col.metric("Passing checks", pass_count)
        if overall_status == "BLOCKED":
            st.error("Publication is blocked until the readiness findings are resolved.")
        elif overall_status == "WARN":
            st.warning("No blockers were found, but warnings remain for review.")
        elif overall_status == "READY":
            st.success("No blockers or warnings were found in this audit.")
        if not checks.empty:
            display_columns = [
                "status",
                "label",
                "details",
                "recommendation",
            ]
            display_columns = available_columns(display_columns, checks)
            st.dataframe(checks[display_columns], width="stretch", hide_index=True)
        st.download_button(
            "Download readiness JSON",
            readiness_json_path.read_text(encoding="utf-8"),
            file_name="readiness_audit.json",
            mime="application/json",
        )
        if readiness_md_path.exists():
            st.download_button(
                "Download readiness report",
                readiness_md_path.read_text(encoding="utf-8"),
                file_name="readiness_audit.md",
                mime="text/markdown",
            )

with methods_tab:
    st.markdown(
        """
### MVP methods

- Facility disappearances are labeled as possible closure signals, not confirmed closures.
- Relocation uses a configurable great-circle distance threshold.
- County access is calculated from weighted population points to the nearest active facility.
- The shock score keeps deterioration and vulnerability components visible.
- Candidate locations are ranked by population-weighted distance reduction and threshold recovery.

The score is an exploratory prioritization signal, not a validated clinical measure or
causal estimate.
"""
    )
    brief_path = next((path for path in brief_candidates if path.exists()), None)
    html_brief_path = next((path for path in html_brief_candidates if path.exists()), None)
    if brief_path is not None:
        brief = brief_path.read_text()
        st.download_button(
            "Download policy brief",
            brief,
            file_name="radiology_access_shock_brief.md",
            mime="text/markdown",
        )
    if html_brief_path is not None:
        html_brief = html_brief_path.read_text()
        st.download_button(
            "Download HTML policy brief",
            html_brief,
            file_name="radiology_access_shock_brief.html",
            mime="text/html",
        )
