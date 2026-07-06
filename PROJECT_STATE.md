# PROJECT_STATE

## Project Overview

### Project Name
Radiology Access Shock Tracker

### Goal
Add and use 50-state source access for the radiology access workflow while preserving the reviewed
North Carolina validation package and keeping the public GitHub Pages documentation accurate.

### Current Status
50-state public no-secret data package, production completion auditing, and production data-quality
reporting are implemented and validated on branch `codex/github-page-fixes`. Follow-up production
hardening now requires ACS for production all-state rebuilds, adds a manual GitHub Actions
all-state package workflow, and emits state-by-state readiness gates.

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

### Feature: Production Completion Audit

#### Validation
- `python -m pytest tests/test_production.py tests/test_cli.py::test_production_audit_command_writes_reports -q`: passed.
- `python -m radshock.cli production-audit --config-path config.example.toml --all-states-manifest work/all-states/2026-07-02/summary/data_package_manifest.json --readiness-json desktop_payload/analysis/readiness_audit.json --output-json outputs/production_audit.json --output-md outputs/production_audit.md --force`: generated a `BLOCKED` audit with 4 blockers and 0 warnings.

#### Tests Added
- `tests/test_production.py`: owner/credential checks, all-state package gates, readiness JSON gate, combined audit READY path.
- `tests/test_cli.py`: `production-audit` JSON/Markdown command coverage.

### Feature: Production Data-Quality Reporting

#### Validation
- `python -m pytest tests/test_quality.py tests/test_cli.py::test_data_quality_report_command_writes_single_dataset_reports tests/test_cli.py::test_route_uncertainty_check_command_writes_report -q`: passed.
- `python -m radshock.cli data-quality-report data/snapshots/2026-06-20/facilities.csv --dataset-type facilities --output-json outputs/facilities_quality.json --output-md outputs/facilities_quality.md --force`: PASS for 289 facility rows.
- `python -m radshock.cli route-uncertainty-check data/travel_times/2026-06-20_tract_nearest20_osrm_review.csv --output-csv outputs/route_uncertainty.csv --force`: PASS for 52,680 routed rows, 2,634 origins, 0 high-speed flags, and 0 missing-provider rows.
- `python -m pytest -q`: passed.
- `python -m ruff check .`: passed.
- `python -m mypy src`: passed with no issues in 30 source files.

#### Tests Added
- `tests/test_quality.py`: CSV quality audit, geocoder confidence, identifier crosswalk, route uncertainty, bundled data-quality outputs.
- `tests/test_cli.py`: `data-quality-report` and `route-uncertainty-check` command coverage.

### Feature: All-State Production Rebuild Guardrails

#### Validation
- `python scripts/build_all_states_data_package.py --output-dir work\all-states\missing-key-smoke --force`: failed as expected because `CENSUS_API_KEY` is not visible locally.
- `python scripts/build_all_states_data_package.py --output-dir work\all-states\2026-07-06 --public-report outputs\all_states_data_package.md --allow-missing-acs --force`: generated a staging package with public-source coverage for all 50 states and ACS marked missing.
- Generated `work/all-states/2026-07-06/summary/state_readiness_gates.csv` with 50 state rows; all states remain blocked for human review, geocoding, routing, ACS, and publication.
- `python -m pytest -q`: passed.
- `python -m ruff check .`: passed.
- `python -m mypy src`: passed with no issues in 30 source files.
- `python -m radshock.cli production-audit --config-path config.example.toml --all-states-manifest work/all-states/2026-07-06/summary/data_package_manifest.json --readiness-json desktop_payload/analysis/readiness_audit.json --output-json outputs/production_audit.json --output-md outputs/production_audit.md --force`: generated a `BLOCKED` audit with 4 blockers and 0 warnings.

#### Tests Added
- `tests/test_all_states_package.py`: production ACS key requirement, ACS readiness-gate removal when complete, and state-by-state readiness gate output.

---

## Current Work

### Active Feature
Production hardening.

### Progress
The software now exposes explicit production completion gates plus data-quality reports for
reviewed artifacts. The all-state package builder now fails production ACS rebuilds when the Census
key is missing, and the GitHub workflow `.github/workflows/all-states-data-package.yml` can rebuild
the all-state package from `secrets.CENSUS_API_KEY` once that secret is configured.

### Remaining Work
PR #8 is pushed and auto-merge is queued. GitHub still requires repository review approval before
the queued squash merge can complete. Full production launch remains blocked by the current
`production-audit` findings listed below.

---

## Next Actions

1. Approve PR #8 so queued auto-merge can complete.
2. Set `CENSUS_API_KEY` locally and as a GitHub repository secret, then rerun
   `scripts/build_all_states_data_package.py` or dispatch `all-states-data-package.yml` to add ACS
   socioeconomic context and population points.
3. Resolve all all-state manifest readiness gates, then mark the data package publication status
   only after review evidence is complete.
4. Run human review, geocoding, route matrices, and readiness audits before
   publishing non-NC findings.

---

## Risks

### Open Questions
None for the local implementation.

### Known Issues
- GitHub shows one stale/conflicting open pull request, #5 "Build production readiness reporting".
  The production-audit and data-quality pieces have been ported into the active branch, but PR #5
  may still contain unrelated experimental changes.
- Current `production-audit` blockers: `CENSUS_API_KEY` missing locally, all-state ACS county/tract
  context missing, all-state package `publication_status=not_ready_for_publication`, and 4
  unresolved all-state package readiness gates.

### Technical Concerns
- `--state ALL` prepares 50-state inputs, but it does not remove the existing human-review,
  geocoding, route-matrix, and readiness gates required before publishing real findings.
- ACS socioeconomic context is intentionally absent from the current generated package because
  `CENSUS_API_KEY` was not set in this environment. The key was not found in process/user/machine
  environment variables, GitHub repository secrets, common local env/profile files, Codex global
  state, or PowerShell history.
- CDC/ATSDR SVI is included as contextual vulnerability data only; it is not a mammography access,
  facility-capacity, or clinical outcome measure.

---

## Resume Instructions

Start with `src/radshock/production.py`, `src/radshock/data_quality.py`,
`src/radshock/quality.py`, `scripts/build_all_states_data_package.py`, and `src/radshock/cli.py`.
Verify with `python -m pytest -q`, `python -m ruff check .`, and `python -m mypy src`. Rerun
`radshock production-audit` after `CENSUS_API_KEY` is available and the all-state package is rebuilt.
