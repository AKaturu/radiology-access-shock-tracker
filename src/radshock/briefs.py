from __future__ import annotations

import html
import re
from datetime import date
from typing import Any

import pandas as pd


def generate_policy_brief(
    events: pd.DataFrame,
    county_shocks: pd.DataFrame,
    interventions: pd.DataFrame,
    utilization_change: pd.DataFrame | None = None,
    title: str = "Radiology Access Shock Brief",
    as_of: date | None = None,
    synthetic_data: bool = False,
) -> str:
    as_of = as_of or date.today()
    top_counties = county_shocks.head(5)
    top_interventions = interventions.head(3)
    high_priority = county_shocks[county_shocks["alert_level"].isin(["WARNING", "CRITICAL"])]
    uses_travel_time = _uses_travel_time(county_shocks)
    if synthetic_data:
        caveat = (
            "> Synthetic demonstration data are loaded. Do not interpret these outputs as real "
            "North Carolina facility, county, screening, or utilization findings."
        )
    elif uses_travel_time:
        caveat = (
            "> Facility events are surveillance signals requiring source verification. "
            "County access shocks use reviewed route-time matrix inputs."
        )
    else:
        caveat = (
            "> Facility events are surveillance signals requiring source verification. "
            "Distances are great-circle proxies unless a reviewed road-time backend is used."
        )

    lines = [
        f"# {title}",
        "",
        f"**Analysis date:** {as_of.isoformat()}",
        "",
        caveat,
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
            lines.append(_format_county_shock_line(row, uses_travel_time=uses_travel_time))

    lines.extend(["", "## Facility events", ""])
    if events.empty:
        lines.append("No facility event signals were detected.")
    else:
        for row in events.head(10).itertuples(index=False):
            verification = (
                "requires verification"
                if bool(getattr(row, "requires_verification", True))
                else "verified"
            )
            lines.append(
                f"- **{row.event_type}** - {row.facility_name} (`{row.facility_id}`): "
                f"{row.details} ({verification})."
            )

    lines.extend(["", "## Candidate response locations", ""])
    if top_interventions.empty:
        lines.append("No candidate locations were evaluated.")
    else:
        for row in top_interventions.itertuples(index=False):
            lines.append(
                f"- **{row.candidate_name}** - intervention score "
                f"{row.intervention_score:.1f}; estimated {row.person_miles_reduced:,.0f} "
                "population-weighted person-miles recovered."
            )

    if utilization_change is not None and not utilization_change.empty:
        worst = utilization_change.nsmallest(3, "utilization_delta_per_1000")
        lines.extend(["", "## Utilization signal", ""])
        for row in worst.itertuples(index=False):
            lines.append(
                f"- County `{row.county_fips}` changed by "
                f"{row.utilization_delta_per_1000:+.1f} screening services per 1,000 "
                "beneficiaries."
            )

    lines.extend(
        [
            "",
            "## Interpretation limits",
            "",
            "- A missing facility ID is a possible closure signal, not a confirmed closure.",
            _access_limit_line(uses_travel_time),
            "- Facility capacity is not yet used to allocate patient demand.",
            "- Aggregate CMS trends cannot establish that a facility event caused "
            "utilization changes.",
            "",
            "## Recommended next action",
            "",
            "Verify high-severity events with primary facility or regulator sources, then "
            "prioritize road-network validation and outreach planning for the highest-scoring "
            "counties.",
            "",
        ]
    )
    return "\n".join(lines)


def _uses_travel_time(county_shocks: pd.DataFrame) -> bool:
    if "access_metric" in county_shocks.columns:
        return "travel_time_minutes" in set(county_shocks["access_metric"].astype(str))
    return {
        "mean_travel_time_delta",
        "p90_travel_time_delta",
    }.issubset(county_shocks.columns)


def _format_county_shock_line(row: Any, *, uses_travel_time: bool) -> str:
    if uses_travel_time:
        return (
            f"- **{row.county_name} ({row.alert_level})** - shock score "
            f"{row.shock_score:.1f}; mean travel-time change "
            f"{row.mean_travel_time_delta:+.1f} minutes; 90th-percentile change "
            f"{row.p90_travel_time_delta:+.1f} minutes."
        )
    return (
        f"- **{row.county_name} ({row.alert_level})** - shock score "
        f"{row.shock_score:.1f}; mean distance change "
        f"{row.mean_distance_delta:+.1f} miles; 90th-percentile change "
        f"{row.p90_distance_delta:+.1f} miles."
    )


def _access_limit_line(uses_travel_time: bool) -> str:
    if uses_travel_time:
        return "- Travel times depend on the routing backend, network vintage, and profile."
    return "- Great-circle distance is a screening metric, not a road travel-time estimate."


_MARKDOWN_BOLD = re.compile(r"\*\*(.+?)\*\*")
_MARKDOWN_CODE = re.compile(r"`(.+?)`")
_MARKDOWN_LINK = re.compile(r"\[(.+?)\]\((.+?)\)")


def _render_inline_markdown(text: str) -> str:
    safe = html.escape(text)
    safe = _MARKDOWN_CODE.sub(r"<code>\1</code>", safe)
    safe = _MARKDOWN_LINK.sub(r'<a href="\2">\1</a>', safe)
    safe = _MARKDOWN_BOLD.sub(r"<strong>\1</strong>", safe)
    return safe


def generate_policy_brief_html(markdown_text: str) -> str:
    """Render a conservative standalone HTML version of a generated Markdown brief."""
    body_lines: list[str] = []
    in_list = False
    for line in markdown_text.splitlines():
        if line.startswith("- "):
            if not in_list:
                body_lines.append("<ul>")
                in_list = True
            body_lines.append(f"<li>{_render_inline_markdown(line[2:])}</li>")
            continue
        if in_list:
            body_lines.append("</ul>")
            in_list = False
        if line.startswith("# "):
            body_lines.append(f"<h1>{_render_inline_markdown(line[2:])}</h1>")
        elif line.startswith("## "):
            body_lines.append(f"<h2>{_render_inline_markdown(line[3:])}</h2>")
        elif line.startswith("> "):
            body_lines.append(f"<blockquote>{_render_inline_markdown(line[2:])}</blockquote>")
        elif line.strip():
            body_lines.append(f"<p>{_render_inline_markdown(line)}</p>")
    if in_list:
        body_lines.append("</ul>")
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="utf-8">',
            "<title>Radiology Access Shock Brief</title>",
            "<style>",
            "body{font-family:Arial,sans-serif;line-height:1.5;max-width:900px;"
            "margin:40px auto;padding:0 20px;color:#1f2933}",
            "blockquote{border-left:4px solid #b45309;background:#fff7ed;"
            "padding:12px 16px;margin:16px 0}",
            "h1,h2{color:#111827}",
            "li{margin:6px 0}",
            "</style>",
            "</head>",
            "<body>",
            *body_lines,
            "</body>",
            "</html>",
        ]
    )
