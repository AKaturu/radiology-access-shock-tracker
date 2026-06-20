# Compiled Test Report

Generated from the local validation run on 2026-06-20.

## Result

Status: PASS

## Checks

- `python -m pytest`: 79 passed in 4.12s.
- `python -m ruff check .`: passed.
- `python -m mypy src/radshock`: passed with no issues in 24 source files.
- `python -m pip wheel . -w work/dist`: built the project wheel.
- `radshock readiness-audit --require-travel-time` on
  `work/source-refresh-smoke/analysis-tract-osrm-travel-time`: BLOCKED, 1 blocker, 0 warnings.
  This is expected because the package uses the public OSRM endpoint; the county-centroid
  candidate-placeholder warning has been resolved.
- Secret scan for the supplied Census and OpenRouteService key literals: no matches.
- `scripts/finalize_travel_time_package.py` public-OSRM smoke run completed and correctly
  remained BLOCKED for the public route provider.
- `bash -n scripts/run_self_hosted_osrm_matrix.sh`: passed.
- `bash scripts/run_self_hosted_osrm_matrix.sh` with Geofabrik NC timestamp
  `2026-06-19T20:21:41Z`: routed 52,680 of 52,680 tract-nearest facility pairs through local
  self-hosted OSRM, finalized the matrix, and produced readiness READY with 0 blockers and 0
  warnings.

## Built Wheel

- File: `work/dist/radiology_access_shock_tracker-0.1.0-py3-none-any.whl`
- SHA-256: `EC287D06D4D3FCAF039CF435BDA459840D6BD3C205210016DDEBB106E36B289C`

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
- Self-hosted OSRM production route package:
  `work/self-hosted-osrm/analysis-tract-self-hosted-osrm`, readiness READY with 0 blockers and 0
  warnings. The run used Docker Desktop's WSL-backed Linux engine from Git Bash, OSRM backend
  `ghcr.io/project-osrm/osrm-backend:v6.0.0`, Geofabrik North Carolina OSM data timestamp
  `2026-06-19T20:21:41Z`, and PBF SHA-256
  `fa3f912373958c448bc1651a32f3f531ae55e4525665d111e2ca0fd9ccad553f`.

## Media Evidence

- Screenshots: `docs/assets/github/*.png`
- Walkthrough footage: `docs/assets/github/dashboard-walkthrough.webm`
- Capture script: `scripts/capture_github_assets.mjs`

## Boundary

The screenshots and walkthrough use synthetic demo data. They prove the application workflow and
publication-readiness gates render correctly; they are not real North Carolina findings.
