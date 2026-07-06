# Status

## Current Release
**v0.1.0** (2026-06-19) - MVP release.

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
- 50-state public-source staging package with per-source coverage-gap reporting
- Streamlit dashboard with demo and readiness views
- Synthetic end-to-end demo with blocked readiness audit by default
- OSRM self-hosted travel-time routing workflow
- Desktop release packaging (Windows, macOS, Linux)
- Policy brief generation (HTML and Markdown)

## Validation Status
- **Automated tests**: pytest, ruff, and mypy passing on the active branch
- **Synthetic end-to-end test**: Complete (demo generates synthetic data, analysis, readiness audit, and dashboard)
- **Public-data evaluation**: Partial (reviewed NC FDA MQSA snapshots, Census context, and self-hosted OSRM tract travel-time package are complete; 50-state staging inputs are supported but require state-by-state review, geocoding, routing, and readiness approval before publication)
- **Expert review**: Not completed
- **Institutional validation**: Not completed
- **Prospective clinical validation**: Not completed

## Planned Work
- GitHub governance configuration (branch protection, CODEOWNERS, secrets)
- Later-date reviewed snapshot for trend analysis
- State-by-state review, geocoding, routing, and readiness audits for publication outside North Carolina
- Journal manuscript drafting with provided prompt template
