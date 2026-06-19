from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Radiology Access Shock Tracker", page_icon="📡", layout="wide")
st.title("Radiology Access Shock Tracker")
st.caption("Surveillance for changes in mammography access and potential community impact")

analysis_dir = Path(st.sidebar.text_input("Analysis directory", value="outputs/demo/analysis"))
brief_path = analysis_dir.parent / "briefs" / "policy_brief.md"
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

critical = int(shocks["alert_level"].isin(["WARNING", "CRITICAL"]).sum())
col1, col2, col3, col4 = st.columns(4)
col1.metric("Facility events", len(events))
col2.metric("Counties flagged", critical)
col3.metric("Highest shock score", f"{shocks['shock_score'].max():.1f}")
col4.metric("Best intervention score", f"{interventions['intervention_score'].max():.1f}")

overview, event_tab, county_tab, intervention_tab, methods_tab = st.tabs(
    ["Overview", "Facility events", "County shocks", "Interventions", "Methods"]
)

with overview:
    st.subheader("County shock surveillance")
    fig = px.scatter_map(
        shocks,
        lat="centroid_lat",
        lon="centroid_lon",
        size="shock_score",
        color="alert_level",
        hover_name="county_name",
        hover_data={
            "shock_score": ":.1f",
            "mean_distance_delta": ":+.1f",
            "p90_distance_delta": ":+.1f",
            "poverty_pct": ":.1f",
            "centroid_lat": False,
            "centroid_lon": False,
        },
        zoom=5.7,
        center={"lat": 35.5, "lon": -79.2},
        height=560,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.info("All demonstration data are synthetic. Map points are not real county estimates.")

with event_tab:
    st.dataframe(events, use_container_width=True, hide_index=True)
    st.download_button(
        "Download facility events",
        events.to_csv(index=False),
        file_name="facility_events.csv",
        mime="text/csv",
    )

with county_tab:
    display_columns = [
        "county_name",
        "alert_level",
        "shock_score",
        "mean_distance_miles_before",
        "mean_distance_miles_after",
        "mean_distance_delta",
        "p90_distance_delta",
        "utilization_delta_per_1000",
    ]
    st.dataframe(shocks[display_columns], use_container_width=True, hide_index=True)
    st.download_button(
        "Download county shocks",
        shocks.to_csv(index=False),
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

with methods_tab:
    st.markdown(
        """
### MVP methods

- A facility ID present only in the later snapshot is flagged as an opening.
- A facility ID absent from the later snapshot is flagged as a possible closure.
- Relocation uses a configurable great-circle distance threshold.
- County access is calculated from weighted population points to the nearest active facility.
- The shock score combines positive access deterioration with poverty, rurality, and risk context.
- Candidate locations are ranked by population-weighted distance reduction and threshold recovery.

The score is an exploratory prioritization signal, not a validated clinical measure or
causal estimate.
"""
    )
    if brief_path.exists():
        brief = brief_path.read_text()
        st.download_button(
            "Download policy brief",
            brief,
            file_name="radiology_access_shock_brief.md",
            mime="text/markdown",
        )
