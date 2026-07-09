# Manuscript Working Draft

This is a bounded working draft for a software, methods, or public-health informatics manuscript.
It is not a submission-ready paper and does not claim longitudinal access deterioration, confirmed
closures, clinical validation, or causal utilization effects.

## Working Title

Radiology Access Shock Tracker: A Reproducible Review-Gated Workflow for Mammography Access
Surveillance

## Abstract

### Background

Mammography facility availability can change through listings, relocations, status changes, or
service reductions, but public facility files often lack stable identifiers, verified coordinates,
and clinical capacity fields. Public-health surveillance tools therefore need conservative
provenance controls that distinguish review prompts from confirmed access findings [1,2].

### Objective

To describe an open-source workflow for reviewing mammography facility snapshots, estimating
geographic access changes, and blocking publication when required data-review evidence is missing.

### Methods

The software versions facility snapshots with checksum metadata, compares reviewed snapshots for
facility-event signals, computes population-weighted distance or reviewed travel-time access, and
summarizes vulnerability-adjusted county shock scores. Source workflows cover FDA MQSA, Census ACS
and Gazetteer, CDC PLACES, CDC/ATSDR SVI, HRSA candidate sites, and optional routing packages
[2-9]. Publication-readiness audits require provenance evidence before outputs are labeled ready.

### Results

The current release supports source-access and package-readiness review for 51 jurisdictions: all
50 states plus DC. The all-state package audit reports ACS county and tract context for all 51
jurisdictions, 153 of 153 state readiness gates resolved, and a production audit status of READY
with 0 blockers and 0 warnings. The bundled row-level validation artifact remains limited to a
reviewed North Carolina no-observed-change comparison using MQSA snapshots dated 2026-06-19 and
2026-06-20. In that package, the readiness audit passed with 0 blockers and 0 warnings, all 52,680
route pairs were routed, 0 facility event signals were observed, and all 100 counties had no warning
or critical access-shock alert.

### Conclusions

Radiology Access Shock Tracker demonstrates a conservative, reproducible software workflow for
mammography access surveillance. Its current evidence supports software and methods claims, a
reviewed North Carolina validation package, and all-state package-readiness claims. Longitudinal
access-impact claims require a later reviewed MQSA snapshot, state-specific row-level readiness
packages, and independent expert review.

## Introduction

Timely access to screening mammography is a public-health concern, especially for communities where
travel burden, socioeconomic vulnerability, or facility turnover may reduce access. Public facility
data can support surveillance, but facility listings alone are not enough to assert clinical
availability or access loss. Stable identifiers, geocoded locations, active-service review, routing
provenance, and source limitations must be tracked before findings are published [1,2].

This project addresses that gap by packaging facility comparison, routing, contextual vulnerability,
and publication-readiness checks into a reproducible open-source workflow. The central design choice
is conservative review gating: outputs should fail closed when data provenance is incomplete.

## Methods

### System Design

The package includes command-line workflows, a Streamlit dashboard, production audit reports, and
desktop release packaging. Facility snapshots are stored with metadata and checksums. Comparison
logic labels signals such as new listings, possible closures, relocations, status changes, renames,
and capacity reductions as review prompts rather than confirmed clinical events.

### Data Sources

The workflow uses public FDA MQSA facility listings, Census ACS and Gazetteer context, CDC PLACES,
CDC/ATSDR SVI, and HRSA candidate-site records. The current all-state package covers 51
jurisdictions, including DC. FDA MQSA source fields do not provide stable facility IDs, verified
coordinates, active-service flags, or facility-level annual procedure counts; reviewed fields are
therefore required before row-level publication [2-7].

### Routing and Access Metrics

The validated North Carolina package uses a self-hosted OSRM route-time matrix. The software can
also run great-circle distance calculations for synthetic demonstrations. Routing evidence is
treated as a publication dependency because travel-time outputs are sensitive to network, profile,
and coordinate assumptions [8,9].

### Publication Readiness

Production audits report blockers and warnings for missing provenance, unresolved gates, missing
credentials, and incomplete package evidence. Placeholder all-state facility snapshots are blocked.
Future all-state row-level findings must come from reviewed and geocoded MQSA rows with approved
review statuses.

## Results

The v0.2.0 release includes a 51-jurisdiction package-readiness audit, GitHub Pages documentation,
and desktop release assets for Windows, macOS, and Linux [10]. The all-state package is ready for
publication-gate use, but not for row-level all-state findings.

The reviewed North Carolina package is a no-observed-change validation run. It supports
reproducibility, methods, and workflow-readiness claims. It does not support access deterioration,
confirmed facility closure, or utilization-effect claims.

## Discussion

The main contribution is a transparent review-gated workflow that separates source collection,
human review, routing provenance, readiness auditing, and public presentation. This separation makes
it harder to accidentally publish incomplete or overinterpreted facility signals.

The current release is strongest as a software and methods report. Its main evidence gap is
independent expert review, followed by later-date longitudinal data and prospective clinical or
institutional validation.

## Limitations

- FDA MQSA public data do not include stable tracker IDs, verified coordinates, active-service
  review, or facility-level annual capacity.
- Candidate response locations are planning assumptions, not operational recommendations.
- SVI and PLACES variables provide context but do not validate clinical access outcomes.
- OSRM route times do not include traffic, weather, appointment availability, language access,
  insurance status, referral pathways, or equipment capacity.
- The current reviewed real-data package is limited to North Carolina and same-week snapshots.
- Independent expert review, institutional validation, and prospective clinical validation are not
  complete.

## Data and Code Availability

The code, documentation, production audit outputs, GitHub Pages site, and v0.2.0 desktop release
assets are available in the public GitHub repository. Public-source datasets remain governed by
their original source terms [2-10].

## References

1. US Preventive Services Task Force. Screening for breast cancer: US Preventive Services Task Force
   recommendation statement. JAMA. 2024;331(22):1918-1930. doi:10.1001/jama.2024.5534.

2. U.S. Food and Drug Administration. Mammography Facilities. Updated July 6, 2026. Accessed
   July 9, 2026. https://www.fda.gov/findmammography

3. U.S. Census Bureau. American Community Survey 5-Year Data (2009-2024). Published
   January 29, 2026. Accessed July 9, 2026.
   https://www.census.gov/data/developers/data-sets/acs-5year.html

4. U.S. Census Bureau. Gazetteer Files. Accessed July 9, 2026.
   https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.html

5. Centers for Disease Control and Prevention. PLACES: Local Data for Better Health -
   Methodology. Updated December 7, 2025. Accessed July 9, 2026.
   https://www.cdc.gov/places/methodology/index.html

6. Centers for Disease Control and Prevention/Agency for Toxic Substances and Disease Registry/
   Geospatial Research, Analysis, and Services Program. CDC/ATSDR Social Vulnerability Index
   2022 Database: United States. Updated December 16, 2024. Accessed July 9, 2026.
   https://www.atsdr.cdc.gov/place-health/php/svi/svi-data-documentation-download.html

7. Health Resources and Services Administration. Health Center Program Service Delivery and
   Look-Alike Sites. Updated July 8, 2026. Accessed July 9, 2026.
   https://data.hrsa.gov/data/download

8. Project OSRM. Project OSRM. Accessed July 9, 2026. https://project-osrm.org/

9. OpenStreetMap contributors. Copyright and License. Accessed July 9, 2026.
   https://www.openstreetmap.org/copyright

10. Katuru A. Radiology Access Shock Tracker v0.2.0. GitHub. Released July 7, 2026. Accessed
    July 9, 2026.
    https://github.com/AKaturu/radiology-access-shock-tracker/releases/tag/v0.2.0
