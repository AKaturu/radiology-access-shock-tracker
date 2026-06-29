# Status

## Current Release
**v0.1.0** (2026-06-19) — MVP release.

## Implemented Features
- Immutable facility snapshot versioning with SHA-256 checksums
- Facility event detection: new listings, possible closures, relocations, status changes, renames, capacity reductions
- Population-weighted distance and reviewed travel-time access analysis
- Vulnerability-adjusted county shock scores with sensitivity analysis
- Production readiness auditing (JSON and Markdown reports)
- FDA MQSA public-source refresh workflow with human-review gate
- MQSA geocoding assistance (Census and static providers)
- Reviewed travel-time matrix comparison with route-review templates
- Candidate-site review workflow and intervention ranking
- Census ACS county and tract population-point generation
- HRSA health-center service-delivery candidate site assumptions
- Streamlit dashboard with demo and readiness views
- Synthetic end-to-end demo with blocked readiness audit by default
- OSRM self-hosted travel-time routing workflow
- Desktop release packaging (Windows, macOS, Linux)
- Policy brief generation (HTML and Markdown)

## Validation Status
- **Unit tests**: 80 passed (ruff, mypy passing)
- **Synthetic end-to-end test**: Complete (demo generates synthetic data, analysis, readiness audit, and dashboard)
- **Public-data evaluation**: Partial (real NC FDA MQSA snapshot ingested, real census data fetched, real OSRM travel-time matrix generated for NC tracts; no observed change between 2026-06-19 and 2026-06-20 snapshots)
- **Expert review**: Not completed
- **Institutional validation**: Not completed
- **Prospective clinical validation**: Not completed

## Planned Work
- GitHub governance configuration (branch protection, CODEOWNERS, secrets)
- Later-date reviewed snapshot for trend analysis
- Publication-grade route-time package from self-hosted OSRM workflow
- Journal manuscript drafting with provided prompt template
