# Journal Report Package

This project is ready to support a journal-style software, methods, or informatics report. It is
not yet ready for a longitudinal public-health findings paper because the current reviewed real
snapshots are same-week dates with no observed facility changes.

## Recommended Manuscript Framing

Best fit:

- Software/methods paper.
- Public-health informatics tool report.
- Reproducible surveillance workflow note.
- Brief application note using North Carolina mammography access as the demonstration domain.

Avoid for now:

- Claims that mammography access worsened over time.
- Claims that a facility closure caused utilization changes.
- Claims about facility-level annual capacity.
- Claims that HRSA candidate sites can deliver mammography without additional verification.

## Evidence Bundle Contents

The `dist/journal/` package includes:

- `README_JOURNAL_BUNDLE.md`: plain-language bundle map.
- `MANUSCRIPT_OUTLINE.md`: neutral outline for software and methods drafting.
- `MANUSCRIPT_OUTLINE.md`: suggested manuscript structure.
- `analysis_manifest.json`: provenance for the self-hosted route-time analysis.
- `readiness_audit.md` and `readiness_audit.json`: publication-readiness evidence.
- `policy_brief.md`: generated summary brief.
- `facility_events.csv`: zero event rows for the reviewed comparison.
- `county_shocks.csv`: 100 county rows, 0 warning/critical alerts.
- `intervention_rankings.csv`: 771 HRSA candidate assumptions.
- `sensitivity_analysis.csv`: 5 sensitivity scenarios across 100 counties.
- `matrix_metadata.json`: finalized route matrix row counts and checksums.
- `compiled_test_report.md`: local validation evidence.
- `methods.md`, `data_sources.md`, `operations.md`: supporting documentation.
- selected synthetic GitHub-demo screenshots for visual context.

Large local OSRM graph files are intentionally excluded.
The included dashboard screenshots are synthetic demonstration media; use `analysis_outputs/` for
real-data result tables and readiness evidence.

## Results That Can Be Stated

- The software produced immutable reviewed facility snapshots with checksum metadata.
- The self-hosted OSRM workflow produced a reviewed tract-nearest route-time package.
- The readiness audit passed with 0 blockers and 0 warnings.
- The route matrix included 52,680 route pairs, all routed, with 0 unreachable rows.
- The reviewed `2026-06-19` to `2026-06-20` NC MQSA comparison produced 0 facility event signals.
- All 100 NC counties had no warning or critical access shock in this no-change comparison.
- Sensitivity analysis ran across 5 scenarios.
- HRSA service-delivery sites can be used as candidate planning assumptions, with explicit caveats.

## Limitations To Keep Prominent

- Current real-data findings are a no-change validation run, not a longitudinal trend result.
- FDA MQSA public files do not expose stable facility IDs, coordinates, annual capacity, or a
  facility-level procedure count.
- Coordinates and active status are reviewed fields, not raw FDA fields.
- Tract centroids are still spatial approximations.
- OSRM free-flow driving times do not include traffic, weather, appointment availability, insurance,
  language access, referral pathways, or equipment capacity.
- The shock score is exploratory and not clinically validated.
- Candidate response locations are planning assumptions, not operational recommendations.

## Suggested Manuscript Outline

1. Title
2. Abstract
3. Introduction
4. Objective
5. System Design
6. Data Sources and Review Gates
7. Routing and Access Metrics
8. Publication-Readiness Audit
9. Demonstration Results
10. Sensitivity and Candidate-Site Analysis
11. Limitations
12. Reproducibility and Open-Source Availability
13. Discussion
14. Conclusion
15. Data and Code Availability

Use the manuscript outline and evidence bundle to keep drafts bounded by reviewed artifacts.

## Suggested Target Claim

This repository demonstrates a reproducible, conservative workflow for reviewing MQSA facility
snapshots, calculating mammography access changes with documented routing provenance, and blocking
publication when required provenance is missing.

## Suggested Next Study

After the next FDA MQSA source update, repeat the review workflow for a genuinely later snapshot.
If facility events are observed, verify events against primary facility or regulator sources before
writing a longitudinal access-impact manuscript.
