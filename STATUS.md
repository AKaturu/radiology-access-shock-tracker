# Status

## Current Release
**v0.2.0** (2026-07-07) - 51-jurisdiction production package and desktop release.

## Implemented Features
- Immutable facility snapshot versioning with SHA-256 checksums
- Facility event detection: new listings, possible closures, relocations, status changes, renames, capacity reductions
- Population-weighted distance and reviewed travel-time access analysis
- Vulnerability-adjusted county shock scores with sensitivity analysis
- Production readiness auditing (JSON and Markdown reports)
- Project-level production completion auditing for owners, credentials, all-state data coverage, and analysis readiness
- FDA MQSA public-source refresh workflow with human-review gate
- MQSA geocoding assistance (Census and static providers)
- Reviewed travel-time matrix comparison with route-review templates
- Data-quality, geocoder-confidence, identifier-crosswalk, and route-uncertainty reporting
- Candidate-site review workflow and intervention ranking
- Census ACS county and tract population-point generation
- HRSA health-center service-delivery candidate site assumptions
- 51-jurisdiction public-source package with per-source coverage-gap reporting
- ACS-backed all-state package rebuild workflow using `CENSUS_API_KEY`
- Per-state gate tracking and batch review-worklist preparation
- Streamlit dashboard with demo and readiness views
- Synthetic end-to-end demo with blocked readiness audit by default
- OSRM self-hosted travel-time routing workflow
- Desktop release packaging (Windows, macOS, Linux)
- Release package CI gate for source and journal bundle reproducibility
- Policy brief generation (HTML and Markdown)

## Validation Status
- **Automated tests**: pytest, ruff, and mypy passing on the active branch
- **Synthetic end-to-end test**: Complete (demo generates synthetic data, analysis, readiness audit, and dashboard)
- **Public-data evaluation**: Complete for the all-state package publication gates (51 jurisdictions, ACS county/tract context, 153/153 gates resolved, production audit READY with 0 blockers and 0 warnings). The bundled dashboard findings remain limited to the reviewed NC validation package.
- **Expert review**: Review packet ready; independent review not completed
- **Institutional validation**: Not completed
- **Prospective clinical validation**: Not completed

## Planned Work
- Later-date reviewed snapshot for trend analysis
- Reviewed/geocoded all-state facility snapshot ingestion from completed MQSA review CSVs
- Journal manuscript drafting from the bounded working draft
