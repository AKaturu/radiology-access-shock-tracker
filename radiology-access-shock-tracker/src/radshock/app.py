from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Radiology Access Shock Tracker", layout="wide")
st.title("Radiology Access Shock Tracker")
st.caption("Surveillance for changes in mammography access and potential community impact")

analysis_dir = Path(st.sidebar.text_input("Analysis directory", value="outputs/demo/analysis"))
manifest_path = analysis_dir.parent / "manifest.json"
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
    "utilization": analysis_dir / "utilization_change.csv",
}
missing = [str(path) for path in required.values() if not path.exists()]
if missing:
    st.warning("Run `radshock demo` first. Missing: " + ", ".join(missing))
    st.stop()

events = pd.read_csv(required["events"])
shocks = pd.read_csv(required["shocks"], dtype={"county_fips": str})
interventions = pd.read_csv(required["interventions"], dtype={"county_fips": str})
utilization = pd.read_csv(required["utilization"], dtype={"county_fips": str})
manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

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

overview, event_tab, county_tab, intervention_tab, utilization_tab, methods_tab = st.tabs(
    ["Overview", "Facility events", "County shocks", "Interventions", "Utilization", "Methods"]
)

with overview:
    st.subheader("County shock surveillance")
    hover_data: dict[str, str | bool] = {
        "shock_score": ":.1f",
        "mean_distance_delta": ":+.1f",
        "p90_distance_delta": ":+.1f",
        "centroid_lat": False,
        "centroid_lon": False,
    }
    if "population_newly_over_30_miles" in shocks.columns:
        hover_data["population_newly_over_30_miles"] = ":,.0f"
    fig = px.scatter_map(
        shocks,
        lat="centroid_lat",
        lon="centroid_lon",
        size="shock_score",
        color="alert_level",
        hover_name="county_name",
        hover_data=hover_data,
        zoom=5.7,
        center={"lat": 35.5, "lon": -79.2},
        height=560,
    )
    st.plotly_chart(fig, use_container_width=True)
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
    st.dataframe(event_display, use_container_width=True, hide_index=True)
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
        "shock_threshold_component",
        "mean_distance_miles_before",
        "mean_distance_miles_after",
        "mean_distance_delta",
        "p90_distance_delta",
        "population_newly_over_30_miles",
        "population_newly_over_45_miles",
        "population_newly_over_60_miles",
        "population_nearest_facility_changed",
        "utilization_delta_per_1000",
    ]
    display_columns = [column for column in display_columns if column in filtered_shocks.columns]
    st.dataframe(filtered_shocks[display_columns], use_container_width=True, hide_index=True)
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
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(interventions, use_container_width=True, hide_index=True)
    st.download_button(
        "Download intervention rankings",
        interventions.to_csv(index=False),
        file_name="intervention_rankings.csv",
        mime="text/csv",
    )

with utilization_tab:
    st.dataframe(utilization, use_container_width=True, hide_index=True)
    st.download_button(
        "Download utilization signals",
        utilization.to_csv(index=False),
        file_name="utilization_change.csv",
        mime="text/csv",
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
