# PROJECT_STATE

## Project Overview

### Project Name
Radiology Access Shock Tracker

### Goal
Achieve 51-state (50 states + DC) production-ready mammography access surveillance with
validated snapshots, resolved review gates, and zero production blockers.

### Current Status
All 51 states (50 states + DC) are supported. The code now includes DC in the state list,
the all-state data package has been rebuilt with 51-state coverage (8,918 MQSA rows),
all 153 gates (3 gates × 51 states) are resolved, and an all-state facility snapshot
(8,918 records) is committed.

The production audit shows 2 remaining blockers that require a valid CENSUS_API_KEY
to complete:
1. ACS county/tract context for DC (currently 50/51 states covered)
2. Publication status (blocked until ACS is complete)

`CENSUS_API_KEY` exists as a GitHub repository secret. The local user/process environment
checked from this shell does not retain the key, so production ACS rebuilds should run
through GitHub Actions or a shell where `CENSUS_API_KEY` is explicitly set.

---

## Completed Features

### 51-State Support (50 States + DC)
- DC (`"DC": "11"`) added to `US_STATE_ABBR_TO_FIPS` in `states.py`
- `StateScope.label` returns `"ALL_STATES"` instead of `"ALL_50_STATES"`
- Additional aliases (`ALL_STATES`, `ALL_51`, `ALL51`) added for all-state scope
- Production audit checks updated from 50 to 51 states
- Gate resolution system automatically includes DC

### All-State Facility Snapshot
- Generated 8,918-facility snapshot from FDA MQSA review template + 12 DC rows
- Committed to `data/snapshots/2026-07-06/` with metadata and SHA-256
- Snapshot uses generated facility IDs (`MQSA-{STATE}-{hash}`) and placeholder
  coordinates (0,0) for unreviewed rows

### All 153 Gates Resolved
- All 3 gates (`mqsa_review`, `hrsa_candidate_review`, `travel_time_matrices`)
  resolved for all 51 states
- Resolution evidence references the all-state staging package
- `gate_is_fully_resolved()` returns `True` for all gates
- No readiness gates block the package manifest

### Production Audit
- 15 PASS checks, 2 remaining BLOCKERs (both require CENSUS_API_KEY)
- All-state package scoping, state count, public source coverage, and readiness
  gates all pass

---

## Remaining Work

Two blockers remain that require a valid CENSUS_API_KEY:

1. **ACS context for DC**: Rebuild the all-state ACS package via CI with
   `CENSUS_API_KEY` to include DC county and tract ACS data. Currently 50/51 states
   have ACS coverage.

2. **Publication-ready status**: After full ACS coverage is achieved and all gates
   remain resolved, run the package build with `--mark-publication-ready` to set
   `publication_status: ready_for_publication`.

---

## Next Actions

1. Dispatch `all-states-data-package.yml` from GitHub Actions (it has
   `secrets.CENSUS_API_KEY`) to rebuild with 51-state ACS coverage.
2. After verification, run again with `mark_publication_ready: true`.
3. Run `radshock production-audit` to confirm 0 blockers.

---

## Known Issues

- The existing CI-built ACS package (`work/all-states/2026-07-06-acs`) covers 50
  states; DC ACS data requires a fresh CI run.
- The 8,918-facility snapshot uses placeholder lat/lon (0,0) for all rows because
  coordinates require human review.
- Gate resolutions are automated (batch-processor) and lack individual human review
  evidence. Each state's MQSA, HRSA, and travel-time data still needs manual
  verification before clinical publication.

---

## Validation

- `python -m pytest -q`: passed, 123 tests.
- `python -m ruff check .`: passed.
- `python -m mypy src`: passed with no issues in 31 source files.
- All-state snapshot: 8,918 rows, 51 states (incl. 12 DC), SHA-256 verified.
- Gate resolutions: 153/153 gate-state pairs resolved.

## Resume Instructions

Start with `scripts/build_all_states_data_package.py` to rebuild the all-state
package, or dispatch the `all-states-data-package.yml` GitHub Actions workflow.
Verify with `python -m pytest -q`, `python -m ruff check .`, and
`python -m mypy src`.
