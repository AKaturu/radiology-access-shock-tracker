# Compiled Test Report

Generated from the local validation run on 2026-06-20.

## Result

Status: PASS

## Checks

- `python -m pytest`: 80 passed in 4.61s.
- `python -m ruff check .`: passed.
- `python -m mypy src/radshock`: passed with no issues in 25 source files.
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
- PowerShell parse checks passed for `scripts/package_release.ps1` and
  `scripts/configure_github_governance.ps1`.
- `scripts/package_release.ps1` generated the GitHub source ZIP, journal evidence bundle, and
  release manifest; ZIP inspection found no ignored work/cache/build directories, and required
  journal evidence files were present.
- `scripts/capture_github_assets.mjs` recaptured the GitHub screenshots and walkthrough from the
  synthetic demo with `RADSHOCK_CAPTURE_ALLOW_SYNTHETIC=1`; visual inspection confirmed the warning
  banner and blocked readiness gate are visible.
- `python -m radshock.desktop --check`: validated the bundled reviewed desktop payload.
- `scripts/build_desktop.py`: built a local Windows PyInstaller bundle, and the frozen
  `RadiologyAccessShockTracker.exe --check` validated its bundled payload.

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

- Synthetic demo screenshots: `docs/assets/github/*.png`
- Synthetic demo walkthrough footage: `docs/assets/github/dashboard-walkthrough.webm`
- Capture script: `scripts/capture_github_assets.mjs`

## Boundary

The GitHub screenshots and walkthrough intentionally use synthetic demo data and show the synthetic
warning plus a blocked readiness audit. They are for software demonstration only. The reviewed real
North Carolina self-hosted OSRM package remains available in `desktop_payload/analysis` and the
journal bundle for methods/reproducibility work.

## Desktop Evidence

- Desktop payload: `desktop_payload/analysis`
- Local Windows ZIP: `dist/RadiologyAccessShockTracker-windows-x64.zip`
- Local Windows ZIP SHA-256:
  `0C9934B14581883B6A41EB7CCDD2D92B3A445272AACD02259C7C81BB472CF479`
- GitHub workflow for cross-platform artifacts: `.github/workflows/desktop-release.yml`
