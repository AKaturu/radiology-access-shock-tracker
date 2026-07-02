# PROJECT_STATE

## Project Overview

### Project Name
Radiology Access Shock Tracker

### Goal
Add and use 50-state source access for the radiology access workflow while preserving the reviewed
North Carolina validation package and keeping the public GitHub Pages documentation accurate.

### Current Status
50-state public no-secret data package generated with CDC/ATSDR SVI county context and validation
complete on branch `codex/github-page-fixes`.

---

## Completed Features

### Feature: 50-State Source Access

#### Validation
- `python -m pytest -q`: passed, 90 tests.
- `ruff check .`: passed.
- `mypy src/radshock`: passed with no issues in 27 source files.
- Rendered local Markdown link audit: passed for 12 Markdown files.

#### Tests Added
- `tests/test_adapters.py`: state-scope parsing, CDC PLACES all-state filtering, ACS national
  Gazetteer/ACS joining, HRSA all-state filtering.
- `tests/test_cli.py`: `prepare-mqsa-review --state ALL` coverage and updated metadata assertions.

### Feature: 50-State Public Data Package

#### Validation
- Generated package at `work/all-states/2026-07-02`.
- Public report written to `C:\Users\Abinav Katuru\Documents\Codex\2026-07-02\are\outputs\all_states_data_package.md`.
- Manifest hash validation passed for all 10 generated output artifacts.
- `state_source_summary.csv`: 50 state rows; every state has MQSA, HRSA, CDC PLACES, CDC/ATSDR
  SVI, Census county Gazetteer, and Census tract Gazetteer coverage.

#### Tests Added
- `tests/test_adapters.py`: stable CDC PLACES `MAMMOUSE` measure-ID assertion.

### Feature: CDC/ATSDR SVI County Context

#### Validation
- Generated `context/cdc_atsdr_svi_counties_all_50.csv` with 3,143 county rows.
- `state_source_summary.csv`: all 50 states have CDC/ATSDR SVI county coverage.

#### Tests Added
- `tests/test_adapters.py`: SVI all-50-state filtering and CDC `-999` missing-value handling.

---

## Current Work

### Active Feature
None.

### Progress
All requested implementation, data gathering, docs, and validation updates are complete locally.

### Remaining Work
PR #8 is pushed and auto-merge is queued. GitHub still requires repository review approval before
the queued squash merge can complete.

---

## Next Actions

1. Approve PR #8 so queued auto-merge can complete.
2. Set `CENSUS_API_KEY` and rerun `scripts/build_all_states_data_package.py` to add ACS
   socioeconomic context and population points.
3. Run human review, geocoding, route matrices, and readiness audits before
   publishing non-NC findings.

---

## Risks

### Open Questions
None for the local implementation.

### Known Issues
- GitHub shows one open pull request, #5 "Build production readiness reporting"; no open issue was
  found for the Pages repo.

### Technical Concerns
- `--state ALL` prepares 50-state inputs, but it does not remove the existing human-review,
  geocoding, route-matrix, and readiness gates required before publishing real findings.
- ACS socioeconomic context is intentionally absent from the current generated package because
  `CENSUS_API_KEY` was not set in this environment.
- CDC/ATSDR SVI is included as contextual vulnerability data only; it is not a mammography access,
  facility-capacity, or clinical outcome measure.

---

## Resume Instructions

Start with `scripts/build_all_states_data_package.py`, `src/radshock/states.py`,
`src/radshock/adapters/acs.py`, and `src/radshock/cli.py`. Verify with `python -m pytest -q`,
`ruff check .`, and `mypy src/radshock`. The single next step is to push
`codex/github-page-fixes` and open a PR if the GitHub repo should receive these changes.
