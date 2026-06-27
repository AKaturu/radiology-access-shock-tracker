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
Candidate-site assumptions now have a review-template and finalization gate so intervention
rankings can be kept separate from unreviewed placeholder locations.
GitHub-ready screenshots, walkthrough footage, and a compiled validation report now document the
synthetic demo workflow for the public project front page, while reviewed real-data packages remain
available for explicit research and reproduction workflows.
Repository presentation polish now adds badges, a repository guide, explicit quality gates,
contribution/security links, package project URLs, and clearer publication-boundary language.

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

### Candidate-Site Review Workflow

#### Validation

`prepare-candidate-review` creates a county-centroid candidate review CSV from `data/counties.csv`
with `review_status=needs_review`. `finalize-candidate-review` blocks unapproved rows and emits the
minimal candidate schema accepted by `radshock analyze`. Candidate IDs, coordinates, and duplicate
rows are now validated before intervention ranking. If a candidate review sheet is passed directly
to analysis, unapproved `review_status` rows are rejected.

#### Tests Added

Tests cover candidate review-template generation, unapproved-row blocking, analysis-ready
finalization, stricter candidate validation, direct analysis rejection of unapproved review sheets,
and CLI prepare/finalize behavior.

### GitHub Media and Compiled Validation Bundle

#### Validation

The dashboard overview chart no longer depends on external map tiles for screenshot rendering.
GitHub-page screenshots and walkthrough footage were recaptured from the synthetic demo so the
public project can be demonstrated without presenting real-data outputs as casual demo findings.
The README links to the media guide and compiled local validation report.

#### Tests Added

No new unit tests were required for static media. The capture script was exercised against the
local Streamlit app, and the full validation gate passed after the dashboard changes.

## Current Work

### Active Feature

Production readiness hardening.

### Progress

#### Latest Production-Readiness Pass

- `prepare-hrsa-candidate-review` was added. It converts the HRSA Health Center Program Service
  Delivery and Look-Alike Sites CSV into reviewed candidate assumptions, keeping active NC
  service-delivery rows by default and excluding administrative-only rows.
- `finalize-candidate-review` now supports finalized metadata output. The former county-centroid
  candidate placeholders were replaced with 771 HRSA service-delivery candidate assumptions across
  92 NC counties: 592 fixed-site, 118 seasonal fixed-site, and 61 mobile-stop assumptions.
  Provenance is tracked in `data/candidate_sites_review.metadata.json` and
  `data/candidate_sites.metadata.json`.
- Source archive commands now expose `--retrieved-on` so dated raw-source archives can be created
  deterministically from the CLI.
- `carry-forward-mqsa-review` was added. It copies reviewed MQSA fields only when
  `source_record_hash` matches a prior reviewed CSV and writes carry-forward metadata.
- A live FDA MQSA source was archived for `2026-06-20`, an NC review template was prepared, and
  all 289 rows matched unchanged reviewed `2026-06-19` source hashes. The carried-forward review
  finalized successfully and was ingested as
  `work/source-refresh-smoke/snapshots/2026-06-20`.
- The `2026-06-19` and `2026-06-20` reviewed real snapshots support only a no-observed-change
  claim for that interval because all source hashes matched.
- `fill-travel-time-review` now supports `--max-origins` for resumable route batches.
- `finalize-travel-time-review` now supports finalized matrix metadata with input/output checksums,
  provider URLs, retrieved timestamp range, and row counts.
- Hosted OpenRouteService successfully filled part of the tract nearest-20 worklist, but the
  provided free key returned `{"error": "Quota exceeded"}` before completion. The partial ORS
  review remains in `work/source-refresh-smoke/travel-time/2026-06-20_tract_nearest20_openrouteservice_review.csv`.
- A complete uniform OSRM-compatible tract nearest-20 route review was generated at
  `data/travel_times/2026-06-20_tract_nearest20_osrm_review.csv` with 52,680 routed rows, zero
  unreachable rows, and provider metadata on every row. It was finalized to
  `data/travel_times/2026-06-20_tract_nearest20_osrm_matrix.csv` with metadata at
  `data/travel_times/2026-06-20_tract_nearest20_osrm_matrix.metadata.json`.
- A real tract-based travel-time analysis package was generated at
  `work/source-refresh-smoke/analysis-tract-osrm-travel-time` using the two reviewed snapshots,
  `data/population_points_tracts.csv`, `data/counties.csv`, `data/candidate_sites.csv`, and the
  finalized OSRM tract matrix for both periods. It produced 100 county records with zero
  warning/critical alerts, as expected for unchanged facility snapshots.
- `readiness-audit --require-travel-time` was tightened to block public OSRM route-provider
  provenance and warn on county-centroid placeholder candidates. After replacing placeholders with
  HRSA service-delivery assumptions, the public-OSRM real tract package returns `BLOCKED` with 1
  blocker and 0 warnings; the remaining blocker is the testing-grade public OSRM route provider.
- The route-provider readiness gate now requires provider, profile, traffic assumption, routing
  engine deployment/version, and OSM map extract source/date/checksum provenance. Self-hosted OSRM
  provenance passes; incomplete private routing provenance blocks publication.
- `.github/workflows/self-hosted-osrm-travel-time.yml`,
  `scripts/run_self_hosted_osrm_matrix.sh`, and `scripts/finalize_travel_time_package.py` were
  added. The manual workflow builds an OSRM MLD graph from the Geofabrik North Carolina extract,
  refills the tract nearest-20 route review through `127.0.0.1`, finalizes a self-hosted matrix,
  and emits a readiness-audited analysis package artifact.
- The reviewed 2026-06-19 and 2026-06-20 facility snapshots plus FDA source metadata were promoted
  to `data/snapshots/` and `data/source_metadata/` so the self-hosted OSRM workflow can reproduce
  the real package on GitHub's Ubuntu runner without ignored `work/` files.
- The policy brief generator now describes travel-time shocks in minutes when road-time outputs are
  supplied.
- `.github/CODEOWNERS`, `.github/branch-protection.main.json`,
  `.github/branch-protection.master.json`, and `scripts/configure_github_governance.ps1` were
  added. Local execution confirmed GitHub settings cannot be applied from this machine because
  PowerShell script execution is restricted by default and the GitHub CLI is not installed/on PATH.
- Latest validation after this pass: `python -m pytest` passed with 79 tests,
  `python -m ruff check .` passed, `python -m mypy src/radshock` passed, and the real tract
  travel-time readiness audit correctly reports `BLOCKED` for the testing-grade OSRM route
  provider. A public-OSRM finalizer smoke run completed and correctly remained blocked. After the
  Windows reboot, Docker Desktop's WSL-backed Linux engine and Git Bash were usable locally; the
  self-hosted OSRM workflow routed 52,680 of 52,680 tract-nearest pairs with zero unreachable/error
  rows and wrote a readiness `READY` package with 0 blockers and 0 warnings at
  `work/self-hosted-osrm/analysis-tract-self-hosted-osrm`.
- A same-day FDA MQSA refresh was run on 2026-06-20 at `work/mqsa-review-2026-06-20-live`.
  The fresh public ZIP SHA-256 matched the promoted 2026-06-20 source archive
  (`9aa978827386629891acc4fed87e50964de10bd3d681b47b916c78ec39a4141c`). Carry-forward review
  matched all 289 NC source-record hashes, approved all 289 rows, left 0 rows needing review, and
  finalized a work-only snapshot that is byte-for-byte identical to `data/snapshots/2026-06-20`.
  Snapshot comparison produced 0 event rows, so this confirms no same-day source delta but does not
  create a later-date snapshot for trend claims.
- GitHub and journal handoff packaging was added. `docs/GITHUB_PUBLISHING.md` documents a clean
  GitHub push, Pages setup from `/docs`, and governance setup. `docs/index.md` provides a GitHub
  Pages landing page. `docs/JOURNAL_REPORT_PACKAGE.md` and `docs/CHATGPT_JOURNAL_PROMPT.md`
  package the analysis for a conservative software/methods manuscript draft. `scripts/package_release.ps1`
  builds a clean source ZIP and a journal evidence bundle while excluding ignored local build files
  and OSRM graph artifacts.
- Release packaging was validated locally. The packager generated the GitHub source ZIP, journal
  evidence bundle, and release manifest under `dist/`; ZIP inspection found no ignored
  work/cache/build directories, and the journal bundle contained the required manuscript prompt,
  manifest, route metadata, readiness audit, policy brief, figure, and validation files.

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
- A county-centroid candidate review template was prepared at
  `work/source-refresh-smoke/candidates/2026-06-19_county_centroid_candidate_review.csv` with 100
  placeholder rows, all still marked `needs_review`.
- Candidate review metadata was written to
  `work/source-refresh-smoke/candidates/2026-06-19_county_centroid_candidate_review.metadata.json`.
- GitHub-page assets were generated under `docs/assets/github/`, including desktop screenshots,
  a mobile overview screenshot, and `dashboard-walkthrough.webm`.
- `docs/GITHUB_PAGE_ASSETS.md` documents how to use/regenerate the media assets.
- `docs/validation/COMPILED_TEST_REPORT.md` records the latest local validation run, including
  pytest, ruff, mypy, wheel build, demo smoke generation, Streamlit health check, and the wheel
  SHA-256.
- Latest validation for the media/test bundle: `python -m pytest --junitxml
  work/validation/pytest-junit.xml` passed with 66 tests, `python -m ruff check .` passed,
  `python -m mypy src/radshock` passed, `python -m pip wheel . -w work/dist` built
  `radiology_access_shock_tracker-0.1.0-py3-none-any.whl`, and Streamlit health returned HTTP 200.
- The GitHub-page assets were later recaptured from
  `work/self-hosted-osrm/analysis-tract-self-hosted-osrm` with the dashboard synthetic-warning
  guard enabled. That pass showed the reviewed real-data no-observed-change validation package,
  readiness `READY`, 0 blockers, and 0 warnings before the public demo posture was switched back
  to synthetic-first.
- Intermediate validation after the real-data media refresh: `python -m pytest` passed with 79
  tests, `python -m ruff check .` passed, `python -m mypy src/radshock` passed, and the capture
  script completed against the reviewed package before the public assets were switched back to the
  synthetic demo.
- The GitHub-page assets were then intentionally recaptured from `outputs/demo/analysis` with
  `RADSHOCK_CAPTURE_ALLOW_SYNTHETIC=1`. The public README and Pages demo are now synthetic-first
  again, with visible synthetic warnings and a blocked readiness audit. The reviewed real-data
  package is preserved in `desktop_payload/analysis` and the journal bundle for deliberate
  research/reproduction use.
- Latest validation after restoring synthetic-first GitHub demo assets: `python -m pytest` passed
  with 80 tests, `python -m ruff check .` passed, `python -m mypy src/radshock` passed,
  `scripts/package_release.ps1` parsed successfully, and visual inspection confirmed the overview
  and readiness screenshots show the synthetic warning and blocked readiness gate.
- Desktop packaging support was added. `desktop_payload/analysis` tracks the compact reviewed
  self-hosted OSRM analysis package for offline dashboard use, `radshock.desktop` launches the
  bundled Streamlit dashboard, `scripts/build_desktop.py` builds a PyInstaller bundle, and
  `.github/workflows/desktop-release.yml` builds Windows ZIP, macOS DMG, and Linux tar.gz
  downloads on native GitHub runners. A local Windows PyInstaller bundle was built and
  `RadiologyAccessShockTracker.exe --check` validated its bundled payload.
- Latest validation after desktop packaging: `python -m pytest` passed with 80 tests,
  `python -m ruff check .` passed, `python -m mypy src/radshock` passed,
  `python -m radshock.desktop --check` passed, and the local Windows desktop ZIP was generated at
  `dist/RadiologyAccessShockTracker-windows-x64.zip`.
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

- Publish the generated source ZIP from `dist/github/` to GitHub, enable GitHub Pages from `/docs`,
  and manually run the `desktop release` GitHub Actions workflow to produce GitHub-hosted Windows,
  macOS, and Linux downloads.
- Optionally rerun the manual `self-hosted OSRM travel-time package` GitHub Actions workflow to
  produce a CI-hosted route-time artifact.
- Apply GitHub branch protection, repository secrets, and code-owner review in GitHub itself after
  installing/authenticating `gh` with repo admin access.
- Obtain a later real reviewed snapshot after a future FDA MQSA source update before making any
  trend or deterioration claim beyond "no observed change between 2026-06-19 and 2026-06-20."

## Next Actions

1. Run the GitHub governance setup from an authenticated admin shell:
   `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\configure_github_governance.ps1 -Apply`.
2. Publish the source ZIP from `dist/github/` to a new GitHub repository and enable Pages from
   `/docs`.
3. Run the `desktop release` workflow on GitHub and attach/download the generated Windows, macOS,
   and Linux artifacts.
4. Use the journal bundle from `dist/journal/` with `docs/CHATGPT_JOURNAL_PROMPT.md` to draft a
   conservative software/methods manuscript.
5. Pull and review a later MQSA source snapshot after the next FDA source update before making
   actual change claims.

## Risks

### Open Questions

- Who should be assigned as GitHub source-review owners for branch protection?
- Which later reviewed snapshot date should be used for the first real change analysis?

### Known Issues

- Live FDA, CDC, Census geocoding, and CMS integrations were not all end-to-end verified against
  live endpoints in CI.
- Great-circle distance remains the default demo method.
- The complete tract OSRM travel-time matrix is a testing artifact with real provider output from
  the public OSRM-compatible endpoint. The repository now includes a self-hosted OSRM generation
  workflow, and the local self-hosted OSRM package is readiness `READY`; the public-OSRM matrix
  remains a testing artifact.

### Technical Concerns

- ACS Census API queries require an API key under current official documentation.
- CMS and public-data schemas can change by release, so fixture tests must be maintained.
- Geocoder matches can be ambiguous and must remain subject to manual review.
- Travel-time matrix validity depends on upstream routing assumptions and network vintage.
- Desktop artifacts are currently unsigned; public releases may trigger Windows SmartScreen or
  macOS Gatekeeper warnings until code signing/notarization is configured.
- Sensitivity scenarios test score robustness but do not clinically validate the score.

## Resume Instructions

Continue from the current Git worktree. Inspect `git status`, rerun the full validation gate if new
changes are made, and do not publish real facility-status claims without independent verification.
