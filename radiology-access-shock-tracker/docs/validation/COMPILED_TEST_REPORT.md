# Compiled Test Report

Generated from the local validation run on 2026-06-20 at 00:00 America/New_York.

## Result

Status: PASS

## Checks

- `python -m pytest`: 72 passed in 5.37s.
- `python -m ruff check .`: passed.
- `python -m mypy src/radshock`: passed with no issues in 23 source files.
- `python -m pip wheel . -w work/dist`: built the project wheel.
- `radshock readiness-audit --require-travel-time` on
  `work/source-refresh-smoke/analysis-tract-osrm-travel-time`: READY, 0 blockers, 0 warnings.
- Secret scan for the supplied Census and OpenRouteService key literals: no matches.
- Streamlit health check at `http://127.0.0.1:8781/_stcore/health`: HTTP 200.

## Built Wheel

- File: `work/dist/radiology_access_shock_tracker-0.1.0-py3-none-any.whl`
- SHA-256: `E52518E116D34FDA2F51CD1AF8E68A2BACA20BA242A946F5BFE3AFF11E530B61`

## Real Artifact Evidence

- Second reviewed MQSA snapshot:
  `work/source-refresh-smoke/snapshots/2026-06-20`.
- Complete tract nearest-20 OSRM route review:
  `data/travel_times/2026-06-20_tract_nearest20_osrm_review.csv` with 52,680 routed rows.
- Final tract travel-time matrix:
  `data/travel_times/2026-06-20_tract_nearest20_osrm_matrix.csv` with 52,680 rows.
- Real travel-time package:
  `work/source-refresh-smoke/analysis-tract-osrm-travel-time`, readiness READY.

## Media Evidence

- Screenshots: `docs/assets/github/*.png`
- Walkthrough footage: `docs/assets/github/dashboard-walkthrough.webm`
- Capture script: `scripts/capture_github_assets.mjs`

## Boundary

The screenshots and walkthrough use synthetic demo data. They prove the application workflow and
publication-readiness gates render correctly; they are not real North Carolina findings.
