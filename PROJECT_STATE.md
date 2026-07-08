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
The local Windows bundle was built and smoke-checked successfully. Release `v0.2.0` is published
with Windows, macOS, and Linux assets.

Post-release housekeeping is complete as of 2026-07-07: local `main` is aligned to `origin/main`,
the stale merged local branches were pruned, GitHub Pages is built from `main` `/docs`, `main`
branch protection was applied from `.github/branch-protection.main.json`, repository auto-merge is
enabled, merged branches are auto-deleted, and `CENSUS_API_KEY` was refreshed in repository
secrets.

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

### Expert Review and Manuscript Preparation
- `docs/EXPERT_REVIEW_PACKET.md` defines the independent-review scope, checklist, evidence links,
  and sign-off record needed before marking expert review complete.
- `docs/MANUSCRIPT_DRAFT.md` contains a bounded software/methods working draft that avoids
  longitudinal, clinical, causal, and row-level all-state claims.
- README, STATUS, and GitHub Pages docs link the new review and manuscript materials.

### GitHub Governance and Publishing
- GitHub Pages is enabled and built from `main` `/docs`.
- `main` branch protection requires the `test` and `release-package` status checks, conversation
  resolution, admin enforcement, and no force pushes or deletions.
- Repository auto-merge is enabled.
- Merged branch auto-deletion is enabled.
- `CENSUS_API_KEY` is configured in GitHub secrets.

### Release Package CI Hardening
- `.github/workflows/tests.yml` includes a `release-package` job that regenerates the source ZIP and
  journal bundle and verifies manifest paths, byte counts, and SHA-256 hashes.
- Branch-protection templates require both `test` and `release-package`.
- `tests/test_release_package_contract.py` checks that release package inputs are tracked repo
  artifacts and that the deleted `2026-07-06` placeholder snapshot directory is not unignored.

### Supply-Chain Security Hardening
- Dependabot is configured for Python dependencies and GitHub Actions.
- CodeQL static analysis is configured for Python.
- Reusable GitHub Actions are pinned to full-length commit SHAs.
- Future desktop releases publish `.sha256` files for downloadable artifacts and a direct-dependency
  CycloneDX SBOM generated from `pyproject.toml`.
- `tests/test_supply_chain_security.py` enforces the pinned-action, Dependabot, CodeQL, checksum,
  and SBOM contracts.

---

## Remaining Work

No current production-audit blockers remain for the all-state package.

Remaining production hardening work:

- Complete independent expert review using `docs/EXPERT_REVIEW_PACKET.md`.
- Ingest a future all-state facility snapshot only from an actual reviewed MQSA CSV with real
  coordinates and approved statuses.
- Refresh FDA MQSA after the next source update to create a genuinely longitudinal comparison.
- Complete state-specific row-level routing/readiness packages before publishing non-NC findings.
- Expand the manuscript draft only within the current evidence boundaries until longitudinal and
  expert-review evidence exists.
- Add platform code signing and macOS notarization before treating desktop downloads as fully
  trusted end-user binaries.

---

## Known Issues

- `OPENROUTESERVICE_API_KEY` is not configured in the local shell or repository secrets. This is
  only required for hosted OpenRouteService route-time drafts; the production route-time path uses
  reviewed/self-hosted OSRM artifacts.
- A production facility snapshot still requires an actual reviewed MQSA CSV with real
  facility IDs, coordinates, active flags, and approved statuses. The repo no longer
  stores placeholder snapshot rows as production data.
- Independent expert review, institutional validation, and prospective clinical validation remain
  incomplete.

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
- GitHub Release `v0.2.0`: published with Windows ZIP, macOS DMG, and Linux tarball.
- GitHub Pages: built from `main` `/docs`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\package_release.ps1`: rebuilt
  source and journal bundle artifacts successfully.
- `release-package` CI job: added to regenerate and verify source/journal package artifacts.
- Supply-chain hardening: Dependabot, CodeQL, pinned Actions, release checksums, and SBOM generation
  added.
- `gh secret list`: `CENSUS_API_KEY` present and refreshed on 2026-07-08 UTC.
- `gh api repos/AKaturu/radiology-access-shock-tracker`: `allow_auto_merge=true` and
  `delete_branch_on_merge=true`.
- Local `main`: aligned with `origin/main` after resolving stale local divergence.

## Resume Instructions

Start from `main`, which is aligned with `origin/main`. The next highest-evidence task is to send
`docs/EXPERT_REVIEW_PACKET.md` and the current release evidence to an independent reviewer, then
record the dated decision before changing expert-review status to complete.
