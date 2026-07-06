# Radiology Access Shock Tracker — Project State

## Overview
Open-source surveillance for changes in mammography access and community impact across US counties.

## Current Status
MVP committed. Pipeline includes FDA MQSA source ingestion, HRSA candidate-site assumptions, OSRM travel-time routing, change detection, sensitivity analysis, and production readiness auditing. All 50 states supported for ACS/Gazetteer census context.

### Gate Resolution Tracking
Readiness gates (`mqsa_review`, `hrsa_candidate_review`, `travel_time_matrices`) track per-state human-review progress:
- **CLI commands**: `resolve-gate`, `unresolve-gate`, `gate-status`
- **Storage**: `work/gate_resolutions.json` (gitignored, per-deployment state)
- **Build integration**: `--mark-publication-ready` flag blocks if any gates unresolved
- **Production audit**: `readiness_gates` domain in `audit-production-config`

## Remaining Work
1. Human review of MQSA rows for all 50 states — geocode, approve active status, snapshot
2. HRSA candidate review for all 50 states — approve candidate sites
3. Travel-time matrices for all 50 states — OSRM routing for each state
4. Per-state gate resolution after each review
5. Rebuild all-states data package with `--mark-publication-ready` when all gates resolved

## Per-State Processing Workflow

### Automated steps (via scripts and CI):
```bash
# 1. Prepare MQSA review worklist
python -m radshock fetch-fda-mqsa --force
python -m radshock prepare-mqsa-review <archive> --state <ST> --output-csv mqsa_review_<ST>.csv --force

# 2. Geocode (automated coordinate fill)
python -m radshock geocode-mqsa-review mqsa_review_<ST>.csv --provider census --output-csv mqsa_review_<ST>_geocoded.csv --overwrite-coordinates --force
```

### Human review required:
- Verify geocoding accuracy in `mqsa_review_<ST>_geocoded.csv`
- Set `active=1` and `review_status=reviewed` for active facilities
- Fix incorrect coordinates

### Finalization (after human review):
```bash
# 3. Finalize and ingest snapshot
python -m radshock finalize-mqsa-review <reviewed.csv> --output-csv facilities_<ST>.csv --force
python -m radshock ingest-snapshot facilities_<ST>.csv --as-of YYYY-MM-DD --source-name fda-mqsa-public

# 4. Resolve gate
python -m radshock resolve-gate mqsa_review <ST> --evidence "<reference>"
```

### Batch orchestration:
```bash
python scripts/process_single_state.py <ST> [--step STEP1 STEP2 ...]
```

### All-states data package:
```bash
python scripts/build_all_states_data_package.py --api-key $CENSUS_API_KEY [--mark-publication-ready]
```

## Key Files
- `src/radshock/gates.py` — Gate resolution data model
- `src/radshock/cli.py` — Gate CLI commands (resolve-gate, unresolve-gate, gate-status)
- `scripts/build_all_states_data_package.py` — All-states ACS/Gazetteer build
- `scripts/process_single_state.py` — Per-state data preparation orchestrator
- `scripts/run_self_hosted_osrm_matrix.sh` — Self-hosted OSRM travel-time pipeline
- `work/gate_resolutions.json` — Per-state gate resolution state (gitignored)

## Tools
- **pytest**: `python -m pytest`
- **ruff**: `python -m ruff check src/ tests/ scripts/`
- **mypy**: `python -m mypy src/radshock/`
