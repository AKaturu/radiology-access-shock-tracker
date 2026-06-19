from __future__ import annotations

from datetime import date

import pandas as pd


def generate_policy_brief(
    events: pd.DataFrame,
    county_shocks: pd.DataFrame,
    interventions: pd.DataFrame,
    utilization_change: pd.DataFrame | None = None,
    title: str = "Radiology Access Shock Brief",
    as_of: date | None = None,
) -> str:
    as_of = as_of or date.today()
    top_counties = county_shocks.head(5)
    top_interventions = interventions.head(3)
    high_priority = county_shocks[county_shocks["alert_level"].isin(["WARNING", "CRITICAL"])]

    lines = [
        f"# {title}",
        "",
        f"**Analysis date:** {as_of.isoformat()}",
        "",
        "> This brief is generated from a demonstration surveillance workflow. Distances are "
        "great-circle proxies, not measured road travel times, and the demo data are synthetic.",
        "",
        "## Executive finding",
        "",
        f"The comparison detected **{len(events)} facility-level events** and identified "
        f"**{len(high_priority)} counties** at warning or critical alert level.",
        "",
        "## Highest-priority county shocks",
        "",
    ]
    if top_counties.empty:
        lines.append("No county access deterioration was detected.")
    else:
        for row in top_counties.itertuples(index=False):
            lines.append(
                f"- **{row.county_name} ({row.alert_level})** — shock score {row.shock_score:.1f}; "
                f"mean distance change {row.mean_distance_delta:+.1f} miles; "
                f"90th-percentile change {row.p90_distance_delta:+.1f} miles."
            )

    lines.extend(["", "## Facility events", ""])
    if events.empty:
        lines.append("No openings, closures, relocations, or service reductions were detected.")
    else:
        for row in events.head(10).itertuples(index=False):
            lines.append(
                f"- **{row.event_type}** — {row.facility_name} "
                f"(`{row.facility_id}`): {row.details}."
            )

    lines.extend(["", "## Candidate response locations", ""])
    if top_interventions.empty:
        lines.append("No candidate locations were evaluated.")
    else:
        for row in top_interventions.itertuples(index=False):
            lines.append(
                f"- **{row.candidate_name}** — intervention score {row.intervention_score:.1f}; "
                f"estimated {row.person_miles_reduced:,.0f} population-weighted person-miles "
                f"recovered."
            )

    if utilization_change is not None and not utilization_change.empty:
        worst = utilization_change.nsmallest(3, "utilization_delta_per_1000")
        lines.extend(["", "## Utilization signal", ""])
        for row in worst.itertuples(index=False):
            lines.append(
                f"- County `{row.county_fips}` changed by "
                f"{row.utilization_delta_per_1000:+.1f} screening services per 1,000 beneficiaries."
            )

    lines.extend(
        [
            "",
            "## Interpretation limits",
            "",
            "- A missing facility ID is a possible closure signal and requires verification.",
            "- Great-circle distance is a screening metric, not a road travel-time estimate.",
            "- Facility capacity is not yet used to allocate patient demand.",
            "- Aggregate CMS trends cannot establish that a facility event caused "
            "utilization changes.",
            "",
            "## Recommended next action",
            "",
            "Verify high-severity events with primary facility or regulator sources, then "
            "prioritize "
            "road-network validation and outreach planning for the highest-scoring counties.",
            "",
        ]
    )
    return "\n".join(lines)
