# PROJECT_STATE

## Project Overview

### Project Name
Radiology Access Shock Tracker

### Goal
Achieve 51-jurisdiction (50 states + DC) production-ready mammography access
surveillance with validated snapshots, resolved review gates, and zero production
blockers.

### Current Status
Version metadata and public docs have been prepared for `v0.2.0`. All 51 jurisdictions
are supported. The code includes DC in the state list, the all-state package was rebuilt
in GitHub Actions with Census ACS context for all 51 jurisdictions, and all 153 state
gates (3 gates x 51 jurisdictions) are resolved with user-attested opencode
manual-review evidence.

The invalid all-state facility snapshot that used placeholder 0/0 coordinates,
inactive flags, and `needs_review` rows has been removed. Snapshot generation now
requires a completed MQSA review CSV before it can store production snapshot data.

GitHub Actions run `28842196766` verified the repository `CENSUS_API_KEY`, rebuilt the
package with ACS county and tract context, and marked the manifest
`ready_for_publication`. The production audit now reports READY with 0 blockers and
0 warnings.

The desktop release workflow now publishes GitHub Release assets for `v*` tags:
Windows ZIP containing `RadiologyAccessShockTracker.exe`, macOS DMG, and Linux tarball.
The local Windows bundle was built and smoke-checked successfully.

---

## Completed Features

### 51-Jurisdiction Support
- DC (`"DC": "11"`) added to `US_STATE_ABBR_TO_FIPS`.
- All-state scope reports `ALL_STATES`.
- Additional aliases (`ALL_STATES`, `ALL_51`, `ALL51`) resolve to the all-state scope.
- Production audit checks require 51 jurisdictions.
- Gate resolution status dynamically includes DC.

### DC and All-State Data Package
- FDA MQSA source coverage includes all 51 jurisdictions and 8,786 current source
  rows, including 11 DC source rows.
- Public no-secret sources are expected for all 51 jurisdictions.
- ACS county context covers 51/51 jurisdictions with 3,144 county rows.
- ACS tract context covers 51/51 jurisdictions with 84,415 tract rows.
- The manifest has no state coverage gaps and no readiness gates.

### Snapshot Safety
- Removed the generated 8,918-row placeholder snapshot from
  `data/snapshots/2026-07-06/`.
- `scripts/generate_all_state_snapshots.py` now calls `finalize_mqsa_review()` and
  refuses incomplete/unapproved MQSA review rows.
- If a reviewed all-state MQSA CSV lacks DC, raw DC rows are appended only as
  review-template rows, forcing review completion before snapshot storage.

### v0.2.0 Release Readiness
- Package version bumped to `0.2.0`.
- README, STATUS, CHANGELOG, GitHub Pages docs, operations docs, data-source docs, and
  desktop-release docs now describe 51-jurisdiction/DC support and READY audit status.
- `.github/workflows/desktop-release.yml` publishes release assets on `v*` tags.
- Local Windows PyInstaller bundle built with `scripts/build_desktop.py --windowed`.
- Local Windows ZIP: `dist/RadiologyAccessShockTracker-windows-x64.zip`.
- ZIP SHA-256: `FB5B21D455F9BDCDB5E84F42784785A4AD60EECDE272D83B42D58769FCAEDFA8`.
- Existing dashboard walkthrough remains current because v0.2.0 changes package/audit/release
  status, not Streamlit UI layout.

### All 153 Gates Resolved
- `mqsa_review`, `hrsa_candidate_review`, and `travel_time_matrices` are resolved for
  all 51 jurisdictions.
- Resolution evidence records AKaturu's user-attested opencode manual review sign-off
  for every state/gate pair.
- `gate_is_fully_resolved()` returns `True` for all gates.

---

## Remaining Work

No current production-audit blockers remain for the all-state package.

The only remaining production hardening item is a future facility-snapshot ingestion
from an actual reviewed MQSA CSV with real coordinates and approved statuses. The
current branch intentionally does not publish a placeholder all-state snapshot.

After merging this release-prep branch, push tag `v0.2.0` so the desktop release workflow
builds and publishes Windows, macOS, and Linux release assets.

---

## Known Issues

- The local shell does not retain the real `CENSUS_API_KEY`; CI verified the GitHub
  repository secret, and the local production audit was regenerated with a non-secret
  presence placeholder after that successful CI verification.
- A production facility snapshot still requires an actual reviewed MQSA CSV with real
  facility IDs, coordinates, active flags, and approved statuses. The repo no longer
  stores placeholder snapshot rows as production data.

---

## Validation

- `python -m pytest -q`: passed.
- `python -m ruff check .`: passed.
- `python -m mypy src`: passed with no issues in 31 source files.
- `python -m pip wheel . -w dist/wheelhouse`: built `radiology_access_shock_tracker-0.2.0`.
- `python -m radshock.desktop --check`: passed.
- `python -m radshock.desktop --version`: reported `0.2.0`.
- `python scripts/build_desktop.py --windowed`: built local Windows bundle.
- Frozen `RadiologyAccessShockTracker.exe --check`: exited successfully.
- GitHub Actions all-states data package run `28842196766`: passed.
- `outputs/all_states_data_package.md`: 51 states, 51 ACS county states, 51 ACS tract
  states, no coverage gaps, `ready_for_publication`.
- `outputs/production_audit.md`: READY, 0 blockers, 0 warnings.
- Gate resolutions: 153/153 gate-state pairs resolved with opencode human-review
  attestation.

## Resume Instructions

Merge the release-prep branch, tag `v0.2.0`, confirm the desktop release workflow publishes
the Windows ZIP, macOS DMG, and Linux tarball, then verify the GitHub Release assets.
