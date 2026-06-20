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
- Added nearest-facility caps and metadata sidecars for travel-time review templates.
- Added OSRM-compatible travel-time review draft filling with route provenance.
- Added hosted OpenRouteService Matrix draft filling through `OPENROUTESERVICE_API_KEY`.
- Added a manual self-hosted OSRM GitHub Actions workflow and finalizer for publication-grade
  route-time packages with map extract/profile provenance.
- Added Census-backed NC county context CSV generation and a live county-centroid ORS travel-time
  test matrix.
- Added Census-backed NC tract population-point generation with source metadata and checksums.
- Added candidate-site review template/finalization commands, stricter candidate validation, and
  analysis guards against unapproved candidate review sheets.
- Added HRSA health-center service-delivery candidate review generation and replaced NC
  county-centroid candidate placeholders with reviewed HRSA planning assumptions.
- Added GitHub-ready dashboard screenshots, walkthrough footage, and a compiled local validation
  report.
- Hardened the dashboard overview visualization so screenshots do not depend on external map tiles.
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
