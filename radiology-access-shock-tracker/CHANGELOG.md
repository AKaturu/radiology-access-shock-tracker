# Changelog

## Unreleased

- Renamed disappearance events from `CLOSED` to `POSSIBLE_CLOSURE` and added verification metadata.
- Added shock-score component columns and point-level access-change populations.
- Added stricter manual facility and CMS adapter validation plus mocked PLACES adapter coverage.
- Added CLI snapshot validation, dry-run ingestion, snapshot comparison, and HTML policy briefs.
- Added persistent synthetic-data warnings and filtering/download improvements to the Streamlit app.
- Added source archive/provenance utilities and an FDA MQSA review-template workflow.
- Added an MQSA review finalization gate before real snapshot ingestion.
- Added cached MQSA geocoding support with Census and static providers for candidate coordinates.
- Added reviewed travel-time matrix access comparisons and a CLI export workflow.
- Added shock-score sensitivity analysis scenarios, CLI export, demo output, and dashboard view.
- Added production readiness auditing with JSON and Markdown reports.
- Added travel-time review template and finalization gates for external routing workflows.
- Added OSRM-compatible travel-time review draft filling with route provenance.
- Added hosted OpenRouteService Matrix draft filling through `OPENROUTESERVICE_API_KEY`.
- Added demo readiness-audit outputs and a dashboard readiness view.
- Added analysis-run manifests and automatic readiness reports for `radshock analyze`.
- Added a guarded GitHub Actions workflow for FDA MQSA source-refresh review artifacts.
- Made facility annual capacity optional because FDA/MQSA public data do not provide
  authoritative per-facility capacity.

## 0.1.0 - 2026-06-19

- Added immutable facility snapshot versioning with checksums.
- Added opening, closure, relocation, rename, status, and capacity-change detection.
- Added population-weighted geographic access and county shock scoring.
- Added utilization change summaries and candidate intervention ranking.
- Added synthetic end-to-end demonstration, Streamlit dashboard, policy brief generation, tests, CI, Docker, and public-data adapter interfaces.
