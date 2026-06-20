# PROJECT_STATE

## Project Overview

### Project Name

Radiology Access Shock Tracker

### Goal

Create a rigorous, reproducible North Carolina mammography access-shock surveillance project that
uses synthetic data safely for demos and supports reviewed public-data ingestion paths.

### Current Status

The downloaded MVP has been committed as a baseline. The project now has safer event semantics,
score transparency, adapter validation, reports, CLI behavior, source archiving, FDA/MQSA review
gates, cached geocoding assistance, reviewed travel-time matrix comparisons, docs, and tests.
It now also produces shock-score sensitivity-analysis outputs for reviewer robustness checks.
Production readiness auditing now makes publication blockers and provenance gaps explicit.
Travel-time route-review templates and finalization gates now provide a reproducible path from
external routing outputs to the access engine.
Synthetic demo runs now emit blocked readiness-audit reports by default, and the dashboard includes
a readiness view for audit findings.
Direct `radshock analyze` runs now emit manifests and readiness reports as part of the output
package, so non-demo analyses carry their own initial publication-gate evidence.
The guarded quarterly MQSA source-refresh workflow now produces review artifacts instead of a
placeholder failure, while still requiring human review before any snapshot or findings.
Facility annual capacity is now optional because FDA/MQSA public data do not publish
authoritative per-facility capacity; any capacity proxy must be explicitly reviewed and labeled.
Census-backed tract population points now provide a finer built-in public-data input than the
earlier county-centroid smoke-test points, though travel-time matrices must be regenerated and
reviewed against the tract points before publication.

## Completed Features

### Baseline Recovery

#### Validation

The uploaded ZIP checksum matched the provided SHA-256 file. The extracted MVP was committed as
`91f1418`.

#### Tests Added

Baseline tests existed for changes, access, snapshots, interventions, and demo generation.

### Safety Hardening

#### Validation

Facility disappearances are now `POSSIBLE_CLOSURE` signals with verification metadata, not
confirmed closure claims.

#### Tests Added

Tests now cover safer event labels, score components, adapter validation, mocked PLACES fetching,
CLI snapshot validation, CLI comparison, and snapshot-copy immutability.

### Source Archive and FDA Review Workflow

#### Validation

Raw source files can be archived with checksums and metadata. FDA MQSA fixed-width files can be
converted into a human-review CSV that leaves facility IDs, coordinates, active status, and capacity
blank until reviewed. The live FDA ZIP retrieved on 2026-06-19 used pipe-delimited rows, so the
parser now auto-detects fixed-width versus pipe-delimited source formats.

#### Tests Added

Tests cover local source archiving, overwrite protection, FDA MQSA fixed-width ZIP parsing, and the
observed pipe-delimited FDA layout, plus the CLI review-template workflow.

### MQSA Review Finalization

#### Validation

`finalize-mqsa-review` blocks unapproved review statuses and blank production fields before a
snapshot-ready CSV can be created.

#### Tests Added

Tests cover incomplete review rejection, blank coordinate rejection, successful snapshot-ready
output, and the CLI finalization command.

### MQSA Geocoding Assistance

#### Validation

`geocode-mqsa-review` can fill blank MQSA review coordinate candidates from either a cached Census
Geocoder provider or a deterministic static CSV provider. Geocoder provenance is written into
explicit review columns, cached by normalized address, and never changes `review_status`, so human
approval remains required before finalization.

#### Tests Added

Tests cover blank coordinate filling, overwrite protection, cache reuse, Census response parsing
from a fixture, and the CLI static-provider workflow.

### Reviewed Travel-Time Matrix Access

#### Validation

`compare-travel-time-access` accepts before/after facility snapshots, population points, county
context, and reviewed point-to-facility travel-time matrices. It filters to active facilities,
chooses the fastest reachable facility for each population point, reports route coverage, computes
minute-based county shock scores, and blocks duplicate or negative matrix values.

#### Tests Added

Tests cover fastest active facility selection, threshold-population changes, duplicate matrix
rejection, and the CLI export workflow.

### Shock-Score Sensitivity Analysis

#### Validation

`sensitivity-analysis` re-scores county shock outputs across baseline, mean-access-heavy,
tail-access-heavy, threshold-heavy, and vulnerability-heavy weighting scenarios. The output keeps
baseline score/rank beside alternate score/rank so reviewers can see which county priorities are
stable and which depend on exploratory weights.

#### Tests Added

Tests cover baseline score/rank preservation, threshold-heavy emphasis changes, travel-time shock
component support, missing-component rejection, CLI export, and demo output generation.

### Production Readiness Audit

#### Validation

`readiness-audit` produces JSON and Markdown reports with `READY`, `WARN`, or `BLOCKED` status. It
blocks synthetic manifests, unresolved facility-event verification, missing core outputs, invalid
snapshot checksums, and missing required production artifacts. It warns on missing provenance,
missing sensitivity analysis, missing policy briefs, and distance-only outputs when road time is not
required.

#### Tests Added

Tests cover synthetic/unverified blockers, verified real-data-like audit packages, and CLI report
generation.

### Travel-Time Route Review Workflow

#### Validation

`prepare-travel-time-review` creates point-to-facility routing worklists from reviewed population
and facility files, with optional straight-line prefiltering. `finalize-travel-time-review` blocks
unapproved rows, invalid route statuses, duplicate point/facility pairs, and routed rows without
minutes before emitting the minimal travel-time matrix accepted by
`compare-travel-time-access`. Route-review templates can also be capped to the nearest N facilities
per population point after distance filtering and can emit metadata sidecars with input/output
checksums, filter settings, and row counts.

#### Tests Added

Tests cover active-only pairing, straight-line filtering, routed versus unreachable finalization,
nearest-facility route pruning, incomplete review rejection, and CLI prepare/finalize behavior.

### Demo Readiness Audit and Dashboard View

#### Validation

`radshock demo` now writes `readiness_audit.json` and `readiness_audit.md` beside the analysis
outputs. The Streamlit dashboard reads those audit artifacts when present and displays overall
status, blocker/warning/pass counts, findings, and report downloads.

#### Tests Added

Demo coverage now asserts that synthetic outputs produce a blocked readiness audit.

### Analysis Manifest and Readiness Packaging

#### Validation

`radshock analyze` now writes `manifest.json`, `readiness_audit.json`, and
`readiness_audit.md` into its output directory. The readiness audit and dashboard can find manifests
in either a direct analysis output directory or the parent package layout used by the demo. The
dashboard no longer requires utilization output when the analysis was run without utilization data.

#### Tests Added

Tests cover direct analysis-folder manifest discovery and CLI `analyze` generation of manifest and
readiness reports.

### Guarded MQSA Source-Refresh Workflow

#### Validation

The quarterly GitHub Actions workflow now supports manual dispatch and guarded scheduled execution.
It downloads the FDA MQSA public ZIP, writes source metadata, prepares a state-filtered MQSA review
CSV, and uploads those files as artifacts. It does not finalize snapshots or publish findings.

#### Tests Added

No runtime tests were added for the GitHub-hosted workflow. The local CLI commands used by the
workflow are covered by existing tests.

### Optional Capacity Handling

#### Validation

Facility snapshots and MQSA review finalization no longer require `annual_capacity`. Capacity
reduction events are emitted only when both compared snapshots contain reviewed numeric capacity.
The FDA MQSA national statistics page was checked and reports only aggregate national procedure
counts. NC DHSR's equipment registration database was checked as a potential proxy source, but its
documentation describes in-process working data rather than authoritative MQSA facility capacity.

#### Tests Added

Tests cover MQSA finalization with blank capacity and confirm missing capacity does not create
`SERVICE_REDUCTION` events.

### Census Tract Population Points

#### Validation

`fetch-census-population-points` fetches selected 2024 ACS 5-year tract indicators for North
Carolina, joins them to Census tract Gazetteer internal points, and writes tract-centroid
population points weighted by ACS female population age 50-74. Metadata records source URLs,
row counts, derivation notes, and output checksums.

#### Tests Added

Tests cover tract ACS/Gazetteer merging, zero-weight tract filtering, CLI export, and metadata
checksum generation.

## Current Work

### Active Feature

Production readiness hardening.

### Progress

Latest validation gate completed:

- `python -m pytest` passed with 47 tests.
- `python -m ruff check .` passed.
- `python -m mypy src/radshock` passed.
- `python -m pip wheel . -w work/dist` built the package wheel.
- `radshock demo --output-dir work/demo-smoke-analyze-packaging` regenerated demo outputs.
- `radshock analyze` against those synthetic inputs wrote `manifest.json`, `readiness_audit.json`,
  and `readiness_audit.md` in `work/analyze-smoke-packaging`.
- The generated synthetic analysis readiness audit was `BLOCKED`, with 4 blockers and 2 warnings.
- Streamlit startup smoke test returned HTTP 200 on `127.0.0.1:8772`.
- `radshock fetch-fda-mqsa --output-dir work/source-refresh-smoke/raw --force` downloaded and
  archived the live FDA MQSA ZIP for 2026-06-19 with metadata.
- `radshock prepare-mqsa-review` created an NC review artifact with 289 rows from that archive.
- `python -m pytest` passed with 49 tests after the optional-capacity change.
- `python -m ruff check .` passed.
- `python -m mypy src/radshock` passed.
- `python -m pip wheel . -w work/dist` built the package wheel.
- `finalize-mqsa-review` successfully finalized a matched MQSA smoke row with blank
  `annual_capacity`.
- The real 2026-06-19 NC MQSA review artifact now has all 289 rows completed for
  `facility_id`, `latitude`, `longitude`, `active`, and `review_status`.
- `facility_id` values use deterministic `MQSA-NC-<source_record_hash prefix>` IDs because the FDA
  public extract does not expose a stable facility identifier.
- `active=true` was inferred for all 289 rows from inclusion in the current FDA MQSA
  certified-facility extract.
- The Cherokee Indian Hospital Authority coordinate was spot-reviewed against the official
  `1 Hospital Rd, Cherokee, NC 28719` address and updated to an ArcGIS PointAddress score 100
  candidate. No rows remain marked approximate.
- `finalize-mqsa-review` produced
  `work/source-refresh-smoke/final/facilities_2026-06-19_NC_reviewed.csv` with 289 active records.
- `ingest-snapshot` stored the reviewed real facility snapshot at
  `work/source-refresh-smoke/snapshots/2026-06-19`.
- A real-facility smoke analysis was run at
  `work/source-refresh-smoke/analysis-real-facility-smoke` using the reviewed real facility
  snapshot and existing demo population/county/candidate context. It is intentionally marked
  synthetic and is blocked for publication.
- `prepare-travel-time-review` created
  `work/source-refresh-smoke/travel-time/travel_time_review_real_facility_smoke.csv` with 9,133
  route pairs, but it was not finalized because real reviewed route minutes/provider metadata are
  not available locally.
- `fill-travel-time-review` now supports OSRM-compatible Table API providers. An OSRM public-demo
  draft was generated at
  `work/source-refresh-smoke/travel-time/travel_time_review_real_facility_smoke_osrm_draft.csv`
  with 9,133 routed rows, zero unreachable rows, and `review_status=needs_review` on every row.
- OSRM draft route metadata was written to
  `work/source-refresh-smoke/travel-time/travel_time_review_real_facility_smoke_osrm_draft.metadata.json`.
- `fill-travel-time-review` also supports hosted OpenRouteService Matrix drafts through
  `--provider openrouteservice` / `--provider ors` and `OPENROUTESERVICE_API_KEY`; the key is not
  stored in tracked files and outputs remain `needs_review` by default.
- `fetch-census-county-context` was added and run against the 2024 ACS 5-year API plus 2024 Census
  county Gazetteer. It wrote `data/counties.csv`, `data/census_county_context_2024.csv`,
  `data/population_points.csv`, and `data/census_county_context_2024.metadata.json`.
- `fetch-census-population-points` was added and run against the 2024 ACS 5-year API plus 2024
  Census tract Gazetteer. It wrote `data/population_points_tracts.csv`,
  `data/census_tract_context_2024.csv`, and `data/census_tract_context_2024.metadata.json`.
- The tract point file has 2,634 nonzero-weight tract points across all 100 NC counties. Its
  eligible-population weight total is 1,660,365, matching `data/counties.csv`.
- A tract-based blank route-review worklist was prepared at
  `work/source-refresh-smoke/travel-time/2026-06-19_tract_nearest20_travel_time_review.csv`
  using a 150-mile straight-line cap and nearest 20 facilities per tract. It has 52,680 route
  pairs, covers all 2,634 tract points, and remains entirely `needs_route` / `needs_review`.
- Route-worklist metadata was written to
  `work/source-refresh-smoke/travel-time/2026-06-19_tract_nearest20_travel_time_review.metadata.json`
  with input/output checksums and the pruning settings.
- The Census API key and OpenRouteService key were used only as process environment variables for
  local pulls; secret scans found no committed key values in project files.
- A Census county-centroid route review was prepared with 17,779 route pairs, filled through hosted
  OpenRouteService Matrix API using request pacing, and finalized for testing at
  `data/travel_times/2026-06-19_county_centroid_openrouteservice_matrix.csv`.
- Row-level ORS route minutes/provider metadata were retained at
  `data/travel_times/2026-06-19_county_centroid_openrouteservice_review.csv`; matrix provenance was
  written to `data/travel_times/2026-06-19_county_centroid_openrouteservice_matrix.metadata.json`.
- A same-snapshot travel-time smoke comparison wrote 100 county records to
  `work/source-refresh-smoke/analysis-census-ors-travel-time-smoke/county_travel_time_shocks.csv`
  with zero warning/critical records, as expected for a no-change smoke run.
- Latest validation after Census/ORS data generation support: `python -m pytest` passed with 56
  tests, `python -m ruff check .` passed, and `python -m mypy src/radshock` passed.
- The quarterly MQSA source-refresh workflow is now enabled on its cron schedule, and
  `docs/OPERATIONS.md` records the required external review-owner and credential setup.

### Remaining Work

- Generate and review tract-based travel-time matrices before publishing analysis outputs. The
  current finalized ORS matrix still uses county-centroid testing points.
- Review hosted ORS/free-plan route outputs, provider terms, traffic assumptions, and unreachable
  rows before treating the finalized matrix as publication-grade.
- Add reviewed candidate-site assumptions before publishing intervention rankings.
- Configure GitHub branch protection or required reviewers in the GitHub UI for source-review
  ownership; local files cannot assign organization teams without admin access.
- Add or obtain a second real reviewed snapshot date before publishing change claims.

## Next Actions

1. Generate and review tract-based travel-time matrices using `data/population_points_tracts.csv`.
2. Add reviewed candidate-site assumptions for intervention ranking.
3. Obtain a second reviewed snapshot date and rerun real change analysis.
4. Resolve readiness-audit blockers with the real outputs and explicit snapshot/source metadata.
5. Configure GitHub branch protection or required source-review owners in the GitHub UI.

## Risks

### Open Questions

- Which reviewed FDA/MQSA export format will be used for the first real snapshot?
- Should hosted OpenRouteService be approved for publication use, or should the project use a
  self-hosted routing engine/commercial provider?
- Who should be assigned as GitHub source-review owners for branch protection?
- What prior reviewed snapshot date should be used for the first real change analysis?

### Known Issues

- Live FDA, CDC, Census geocoding, and CMS integrations were not all end-to-end verified against
  live endpoints in CI.
- Great-circle distance remains the default demo method.
- The current county-centroid ORS travel-time matrix is a testing artifact with real provider
  output. It still needs production review and regeneration against the tract population points
  before publication.

### Technical Concerns

- ACS Census API queries require an API key under current official documentation.
- CMS and public-data schemas can change by release, so fixture tests must be maintained.
- Geocoder matches can be ambiguous and must remain subject to manual review.
- Travel-time matrix validity depends on upstream routing assumptions and network vintage.
- Sensitivity scenarios test score robustness but do not clinically validate the score.

## Resume Instructions

Continue from the current Git worktree. Inspect `git status`, rerun the full validation gate if new
changes are made, and do not publish real facility-status claims without independent verification.
