# Compiled Test Report

Software checks refreshed on 2026-07-11. Desktop and wheel artifact evidence below is retained from
the local v0.2.0 validation run on 2026-07-07.

## Result

Status: PASS

## Checks

- `python -m pytest -q`: 160 tests passed.
- `python -m ruff check .`: passed.
- `python -m ruff format --check .`: passed.
- `python -m mypy src/radshock`: passed with no issues in 33 source files.
- `python -m pip wheel . -w dist/wheelhouse`: built the v0.2.0 project wheel.
- `python -m radshock.desktop --check`: validated the bundled reviewed desktop payload.
- `python -m radshock.desktop --version`: reported `Radiology Access Shock Tracker 0.2.0`.
- `python scripts/build_desktop.py --windowed`: built a local Windows PyInstaller bundle.
- Frozen `RadiologyAccessShockTracker.exe --check`: exited successfully with the bundled payload.
- Local Windows release ZIP inspection confirmed
  `RadiologyAccessShockTracker/RadiologyAccessShockTracker.exe` is present.

## Built Wheel

Historical artifact from the 2026-07-07 v0.2.0 validation run:

- File: `dist/wheelhouse/radiology_access_shock_tracker-0.2.0-py3-none-any.whl`
- Size: 81,475 bytes
- SHA-256: `3F39C49C29ACEAD70B847A74C79DDAF30445561E14B672E513FD2BEA6DC34AE3`

## Desktop Evidence

- Desktop payload: `desktop_payload/analysis`
- Local Windows bundle directory: `dist/desktop/RadiologyAccessShockTracker`
- Local Windows executable:
  `dist/desktop/RadiologyAccessShockTracker/RadiologyAccessShockTracker.exe`
- Local Windows ZIP: `dist/RadiologyAccessShockTracker-windows-x64.zip`
- Local Windows ZIP size: 144,412,287 bytes
- Local Windows ZIP SHA-256:
  `FB5B21D455F9BDCDB5E84F42784785A4AD60EECDE272D83B42D58769FCAEDFA8`
- GitHub workflow for cross-platform artifacts: `.github/workflows/desktop-release.yml`

## All-State Production Evidence

- GitHub Actions all-state package run `28842196766`: passed.
- Jurisdictions in scope: 51 (50 states + DC).
- ACS county context coverage: 51/51 jurisdictions.
- ACS tract context coverage: 51/51 jurisdictions.
- All-state readiness gates: none.
- Publication status: `ready_for_publication`.
- Production audit: `READY`, 0 blockers, 0 warnings.

## Media Evidence

- Synthetic demo screenshots: `docs/assets/github/*.png`
- Synthetic demo walkthrough footage: `docs/assets/github/dashboard-walkthrough.webm`
- Capture script: `scripts/capture_github_assets.mjs`

The v0.2.0 changes affect all-state data coverage, audit status, and desktop release packaging.
The Streamlit UI layout did not change, so the existing synthetic walkthrough remains current.

## Boundary

The GitHub screenshots and walkthrough intentionally use synthetic demo data and show the synthetic
warning plus a blocked readiness audit. They are for software demonstration only. The reviewed real
North Carolina self-hosted OSRM package remains available in `desktop_payload/analysis` and the
journal bundle for methods/reproducibility work.

The all-state package is production-audit ready, but the repository intentionally does not publish
placeholder all-state facility snapshots. Future all-state facility snapshots must come from
completed MQSA review CSVs with real facility IDs, coordinates, active flags, and approved review
statuses.
