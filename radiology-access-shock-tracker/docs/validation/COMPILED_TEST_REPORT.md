# Compiled Test Report

Generated from the local validation run on 2026-06-20.

## Result

Status: PASS

## Checks

- `python -m pytest`: 76 passed in 3.57s.
- `python -m ruff check .`: passed.
- `python -m mypy src/radshock`: passed with no issues in 24 source files.
- `python -m pip wheel . -w work/dist`: built the project wheel.
- `radshock readiness-audit --require-travel-time` on
  `work/source-refresh-smoke/analysis-tract-osrm-travel-time`: BLOCKED, 1 blocker, 0 warnings.
  This is expected because the package uses the public OSRM endpoint; the county-centroid
  candidate-placeholder warning has been resolved.
- Secret scan for the supplied Census and OpenRouteService key literals: no matches.

## Built Wheel

- File: `work/dist/radiology_access_shock_tracker-0.1.0-py3-none-any.whl`
- SHA-256: `44E4BD5FE1B1327D668AF0313427DC33130A68A8C25BCE581E4C3B6A7EA431BA`

## Real Artifact Evidence

- Second reviewed MQSA snapshot:
  `work/source-refresh-smoke/snapshots/2026-06-20`.
- Complete tract nearest-20 OSRM route review:
  `data/travel_times/2026-06-20_tract_nearest20_osrm_review.csv` with 52,680 routed rows.
- Final tract travel-time matrix:
  `data/travel_times/2026-06-20_tract_nearest20_osrm_matrix.csv` with 52,680 rows.
- HRSA service-delivery candidate assumptions:
  `data/candidate_sites_review.csv` and `data/candidate_sites.csv` with 771 rows across 92
  counties; no county-centroid placeholders remain.
- Real travel-time package:
  `work/source-refresh-smoke/analysis-tract-osrm-travel-time`, readiness BLOCKED until route
  provider provenance is production-approved.

## Media Evidence

- Screenshots: `docs/assets/github/*.png`
- Walkthrough footage: `docs/assets/github/dashboard-walkthrough.webm`
- Capture script: `scripts/capture_github_assets.mjs`

## Boundary

The screenshots and walkthrough use synthetic demo data. They prove the application workflow and
publication-readiness gates render correctly; they are not real North Carolina findings.
