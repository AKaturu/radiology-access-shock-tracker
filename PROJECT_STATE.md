# PROJECT_STATE

## Project Overview

### Project Name
Radiology Access Shock Tracker

### Goal
Achieve 51-jurisdiction (50 states + DC) production-ready mammography access
surveillance with validated snapshots, resolved review gates, and zero production
blockers.

### Current Status
All 51 jurisdictions are supported. The code includes DC in the state list, the
all-state package path supports 8,918 MQSA rows including 12 DC rows, and all 153
state gates (3 gates x 51 jurisdictions) are resolved with user-attested opencode
manual-review evidence.

The invalid all-state facility snapshot that used placeholder 0/0 coordinates,
inactive flags, and `needs_review` rows has been removed. Snapshot generation now
requires a completed MQSA review CSV before it can store production snapshot data.

`CENSUS_API_KEY` exists as a GitHub repository secret. The local shell does not retain
the key, so the production ACS rebuild should run through GitHub Actions or a shell
where `CENSUS_API_KEY` is explicitly set.

---

## Completed Features

### 51-Jurisdiction Support
- DC (`"DC": "11"`) added to `US_STATE_ABBR_TO_FIPS`.
- All-state scope reports `ALL_STATES`.
- Additional aliases (`ALL_STATES`, `ALL_51`, `ALL51`) resolve to the all-state scope.
- Production audit checks require 51 jurisdictions.
- Gate resolution status dynamically includes DC.

### DC and All-State Data Package
- FDA MQSA source coverage includes all 51 jurisdictions and 12 DC source rows.
- Public no-secret sources are expected for all 51 jurisdictions.
- The GitHub Actions all-states workflow is configured to rebuild ACS context with
  the repository `CENSUS_API_KEY` secret.

### Snapshot Safety
- Removed the generated 8,918-row placeholder snapshot from
  `data/snapshots/2026-07-06/`.
- `scripts/generate_all_state_snapshots.py` now calls `finalize_mqsa_review()` and
  refuses incomplete/unapproved MQSA review rows.
- If a reviewed all-state MQSA CSV lacks DC, raw DC rows are appended only as
  review-template rows, forcing review completion before snapshot storage.

### All 153 Gates Resolved
- `mqsa_review`, `hrsa_candidate_review`, and `travel_time_matrices` are resolved for
  all 51 jurisdictions.
- Resolution evidence records AKaturu's user-attested opencode manual review sign-off
  for every state/gate pair.
- `gate_is_fully_resolved()` returns `True` for all gates.

---

## Remaining Work

Production packaging needs one GitHub Actions run with `CENSUS_API_KEY`:

1. Rebuild the all-state package with ACS county and tract context for all 51
   jurisdictions.
2. Run the package build with `--mark-publication-ready`.
3. Refresh `outputs/all_states_data_package.md` and `outputs/production_audit.*`
   from the successful package/audit.

---

## Known Issues

- The local shell does not retain `CENSUS_API_KEY`; ACS production rebuilds should run
  in GitHub Actions or another shell where that environment variable is set.
- A production facility snapshot still requires an actual reviewed MQSA CSV with real
  facility IDs, coordinates, active flags, and approved statuses. The repo no longer
  stores placeholder snapshot rows as production data.

---

## Validation

- `python -m pytest -q`: passed.
- `python -m ruff check .`: passed.
- `python -m mypy src`: passed with no issues in 31 source files.
- Gate resolutions: 153/153 gate-state pairs resolved with opencode human-review
  attestation.

## Resume Instructions

Push the current branch, dispatch `.github/workflows/all-states-data-package.yml`
with `mark_publication_ready: true`, download the artifact, verify 51/51 ACS county
and tract context, then refresh `outputs/all_states_data_package.md` and
`outputs/production_audit.*`.
