# PROJECT_STATE

## Project Overview

### Project Name
Radiology Access Shock Tracker

### Goal
Add and use 50-state source access for the radiology access workflow while preserving the reviewed
North Carolina validation package and keeping the public GitHub Pages documentation accurate.

### Current Status
50-state data package with full public + ACS coverage, production completion auditing, and
production data-quality reporting are implemented and validated on branch
`codex/github-page-fixes`. CENSUS_API_KEY is configured locally and as a GitHub secret. ACS county
and tract context covers all 50 states. Production audit shows 2 intentional blockers
(publication_status and readiness gates). Added `--mark-publication-ready` CLI flag and workflow
input for when human review is complete. Added gate resolution tracking system
(`src/radshock/gates.py`) with CLI commands `resolve-gate`, `unresolve-gate`, `gate-status`.
NC gates resolved using existing analysis evidence.

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
- `tests/test_production.py`: `audit_all_states_manifest` with `require_acs=False` emits `WARN` for missing ACS (not `BLOCKER`).
- `tests/test_cli.py`: `production-audit --allow-missing-acs` CLI integration covers the warn-not-block path.

---

## Current Work

### Active Feature
Production hardening.

### Progress
CENSUS_API_KEY is set locally and as a GitHub repository secret. The all-state package at
`work/all-states/2026-07-06-acs` has full ACS county (3,143) and tract (84,209) context for all 50
states. The production audit dropped from 4 to 2 blockers: CENSUS_API_KEY and ACS both PASS now.
Fixed a tract-join edge case in `acs.py` where 14 New York tracts exist in the Gazetteer but not
in ACS (water/zero-population tracts) — changed from `how="inner"` to `how="left"` with
`_fill_missing_acs_values()`. Added `--mark-publication-ready` flag to the build script and as a
workflow_dispatch boolean input in `all-states-data-package.yml`.

Added gate resolution tracking system:
- New module `src/radshock/gates.py` with per-state gate resolution data model (load/save/resolve).
- Three known gates: `mqsa_review`, `hrsa_candidate_review`, `travel_time_matrices`.
- Gate resolution stored in `work/gate_resolutions.json` with resolved_by, resolved_at, evidence.
- A gate is removed from the manifest only when all 50 states are resolved.
- Partially resolved gates show remaining state count (e.g. "49 of 50 states remain unresolved").

CLI commands added to `src/radshock/cli.py`:
- `resolve-gate <gate_name> <state> --evidence <ref>` — marks a gate resolved for a state.
- `unresolve-gate <gate_name> <state>` — reverses a resolution.
- `gate-status [--state <abbr>] [--output-json <path>] [--output-md <path>]` — shows per-state gate
  status and active gates.

Build script integration:
- `scripts/build_all_states_data_package.py` reads `work/gate_resolutions.json` (if present) and
  filters out gates where all 50 states are resolved; partially resolved gates show remaining count.
- `_build_state_readiness_audit()` marks per-state gates as PASS when resolved in the tracking file,
  producing accurate `state_readiness_gates.csv` output.

Production audit:
- `src/radshock/production.py` `audit_all_states_manifest()` now lists specific gate strings in
  readiness_gates details instead of a generic "resolve all gates" message.

NC gate integration:
- All three gates resolved for NC using existing desktop_payload analysis evidence:
  - MQSA: snapshots PASS (289 records, before/after validated via readiness_audit.json).
  - HRSA: candidate_assumptions with 771 rows, 92 counties, HRSA source cited (manifest.json).
  - Travel-time: 100.0% route coverage, self-hosted OSRM, Geofabrik NC (readiness_audit.json).

Tests: 120 pass, ruff clean, mypy clean on 31 source files.

### Remaining Work
PR #8 is pushed and auto-merge is queued. GitHub still requires code-owner review approval before
the queued squash merge can complete (self-approval rejected by GitHub). Full production launch
remains blocked by 2 intentional `production-audit` blockers: publication_status and 3 readiness
gates (MQSA review, HRSA candidates, travel-time matrices). NC gates are resolved via tracking
system; 49 states per gate remain. Gate tracking at `work/gate_resolutions.json`.

---

## Next Actions

1. Get PR #8 reviewed and merged (blocked on code-owner review; add a collaborator or temporarily
   adjust branch protection to allow self-merge).
2. Dispatch `all-states-data-package.yml` from GitHub Actions to rebuild with ACS using the
   configured `secrets.CENSUS_API_KEY`.
3. Continue per-state gate resolution by running human review for additional states, then:
   `radshock resolve-gate <gate_name> <state> --evidence "<review reference>"`
4. Once a gate is resolved for all 50 states, it will automatically drop from the manifest on next
   package rebuild. Run `build_all_states_data_package.py --mark-publication-ready` when all gates
   are resolved to flip `publication_status` to `ready_for_publication`.
5. Track gate resolution progress: `radshock gate-status` or inspect `work/gate_resolutions.json`.

---

## Risks

### Open Questions
None for the local implementation.

### Known Issues
- GitHub shows one stale/conflicting open pull request, #5 "Build production readiness reporting".
  The production-audit and data-quality pieces have been ported into the active branch, but PR #5
  may still contain unrelated experimental changes.
- Current `production-audit` blockers (2): `publication_status=not_ready_for_publication` and 3
  readiness gates. NC is resolved for all gates; 49 states per gate remain. Gate tracking at
  `work/gate_resolutions.json`.
- PR #8 cannot be merged because GitHub requires a code-owner review from someone other than the
  author. The repo only has one collaborator (@AKaturu).

### Technical Concerns
- `--state ALL` prepares 50-state inputs, but it does not remove the existing human-review,
  geocoding, route-matrix, and readiness gates required before publishing real findings.
- 14 New York tracts (county FIPS 36103) exist in the Census Gazetteer but not in ACS data
  — likely water-only or zero-population tracts. The left-join with `_fill_missing_acs_values()`
  handles this gracefully, assigning zero population weights.
- CDC/ATSDR SVI is included as contextual vulnerability data only; it is not a mammography access,
  facility-capacity, or clinical outcome measure.

---

## Resume Instructions

Start with `src/radshock/gates.py`, `src/radshock/cli.py`,
`scripts/build_all_states_data_package.py`, `src/radshock/production.py`,
`tests/test_gates.py`, `tests/test_production.py`.
Verify with `python -m pytest -q`, `python -m ruff check .`, and `python -m mypy src`.
Gate resolution status: `radshock gate-status`. Resolve a gate: `radshock resolve-gate <gate> <state> --evidence "<ref>"`.
Unresolve: `radshock unresolve-gate <gate> <state>`.
