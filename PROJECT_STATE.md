# PROJECT_STATE

## Project Overview

### Project Name
Radiology Access Shock Tracker

### Goal
Use 50-state source access for the radiology access workflow while preserving the reviewed North
Carolina validation package and keeping public documentation accurate.

### Current Status
50-state source access, ACS package building, production completion auditing, production
data-quality reporting, and gate-resolution tracking are merged to `main`. PR #8, PR #9, and PR #10
are merged. A cleanup pass removed the accidentally committed nested repository copy and gitlink
from `main`, ported the intended batch-processing scripts to the top-level project, and made the
batch scripts prepare review worklists without marking placeholder data as reviewed.

`CENSUS_API_KEY` exists as a GitHub repository secret. The local user/process environment checked
from this shell does not retain the key, so production ACS rebuilds should run through GitHub
Actions or a new shell where `CENSUS_API_KEY` is explicitly set.

---

## Completed Features

### 50-State Source Access And ACS Context
- FDA MQSA, HRSA, CDC PLACES, CDC/ATSDR SVI, Census Gazetteer, and ACS workflows support all 50 states.
- The all-state package builder can require ACS, emit state-by-state readiness gates, and reject
  `--mark-publication-ready` when review gates remain unresolved.
- The ACS tract join handles Gazetteer tracts that are absent from ACS by preserving rows and filling
  missing ACS values.

### Production And Quality Gates
- `production-audit`, `data-quality-report`, and `route-uncertainty-check` are implemented.
- `src/radshock/gates.py` supports per-state `resolve-gate`, `unresolve-gate`, and `gate-status`.
- NC gates are resolved using the existing reviewed NC analysis package.

### Batch State Preparation
- `scripts/batch_process_all_states.py` prepares checkpointed per-state worklists and review
  checklist CSVs.
- `scripts/process_single_state.py` prepares a single state's MQSA review worklist and geocoding
  output by default.
- `scripts/resolve_geofabrik_url.py` maps state abbreviations to Geofabrik OSM PBF URLs.
- `.github/workflows/self-hosted-osrm-travel-time.yml` now accepts a `state` input, resolves the
  Geofabrik URL when not supplied, and tags the output artifact by state.

---

## Validation

- `python -m pytest -q`: passed, 123 tests.
- `python -m ruff check .`: passed.
- `python -m mypy src`: passed with no issues in 31 source files.
- `python scripts/resolve_geofabrik_url.py CO`: returned the Colorado Geofabrik URL.
- `python scripts/batch_process_all_states.py --states AL --output-dir work\batch-smoke --step --resume`: passed and wrote a batch summary/checklist.
- `python scripts/process_single_state.py AL --step resolve-gates --resolutions-file work\tmp_resolutions.json`: correctly refused to resolve gates without `--resolve-reviewed-gates`.

---

## Remaining Work

Full production publication remains blocked by evidence gates, not by the merge state:

- Non-NC MQSA rows still need human review of facility IDs, coordinates, active status, and review status.
- HRSA candidate rows remain planning assumptions until reviewed.
- All-state travel-time matrices still need provider-backed routing and review.
- Do not mark all 50 states reviewed from automated placeholder outputs.

---

## Next Actions

1. Dispatch `all-states-data-package.yml` from GitHub Actions to rebuild with ACS using
   `secrets.CENSUS_API_KEY`.
2. Use `scripts/batch_process_all_states.py` to prepare review worklists for remaining states.
3. After human review, run `radshock resolve-gate <gate_name> <state> --evidence "<review reference>"`.
4. Only after every state gate is resolved, run the package build with `--mark-publication-ready`.

---

## Known Issues

- PR #5 is closed as superseded. PR #8, PR #9, and PR #10 are merged.
- `CENSUS_API_KEY` is present as a GitHub secret but was not persisted in the local user/process
  environment visible to this shell.
- The previous PR #9 merge introduced a nested `radiology-access-shock-tracker/` copy and a
  `work/github-pr-radshock` gitlink; this cleanup removes both from `main`.

---

## Resume Instructions

Start with `scripts/batch_process_all_states.py`, `scripts/process_single_state.py`,
`scripts/build_all_states_data_package.py`, `src/radshock/gates.py`, and
`tests/test_all_states_package.py`. Verify with `python -m pytest -q`,
`python -m ruff check .`, and `python -m mypy src`.
