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
`compare-travel-time-access`.

#### Tests Added

Tests cover active-only pairing, straight-line filtering, routed versus unreachable finalization,
incomplete review rejection, and CLI prepare/finalize behavior.

### Demo Readiness Audit and Dashboard View

#### Validation

`radshock demo` now writes `readiness_audit.json` and `readiness_audit.md` beside the analysis
outputs. The Streamlit dashboard reads those audit artifacts when present and displays overall
status, blocker/warning/pass counts, findings, and report downloads.

#### Tests Added

Demo coverage now asserts that synthetic outputs produce a blocked readiness audit.

## Current Work

### Active Feature

Production readiness hardening.

### Progress

Latest validation gate completed:

- `python -m pytest` passed with 45 tests.
- `python -m ruff check .` passed.
- `python -m mypy src/radshock` passed.
- `python -m pip wheel . -w work/dist` built the package wheel.
- `radshock demo --output-dir work/demo-smoke-readiness` regenerated demo outputs, including
  `readiness_audit.json` and `readiness_audit.md`.
- The generated synthetic demo readiness audit was `BLOCKED`, with 4 blockers and 2 warnings.
- `radshock demo --output-dir outputs/demo` refreshed the default dashboard demo package.
- Streamlit startup smoke test returned HTTP 200 on `127.0.0.1:8771`.

### Remaining Work

- Use a real FDA MQSA ZIP to generate and human-review the first NC facility CSV.
- Configure and enable the guarded scheduled workflow after repository secrets and source review
  owners are configured.
- Run `readiness-audit` on the first real analysis package and resolve all blockers before sharing.

## Next Actions

1. Review and approve the first real MQSA-derived NC facility CSV.
2. Generate reviewed travel-time matrices with the chosen routing process and finalize them.
3. Run readiness auditing on real analysis outputs and resolve blockers.
4. Configure and enable scheduled workflow execution after repository secrets and source review
   owners are configured.

## Risks

### Open Questions

- Which reviewed FDA/MQSA export format will be used for the first real snapshot?
- Which road-time engine or source should be approved to generate the matrix inputs?

### Known Issues

- Live FDA, CDC, Census geocoding, and CMS integrations were not all end-to-end verified against
  live endpoints in CI.
- Great-circle distance remains the default demo method.

### Technical Concerns

- ACS Census API queries require an API key under current official documentation.
- CMS and public-data schemas can change by release, so fixture tests must be maintained.
- Geocoder matches can be ambiguous and must remain subject to manual review.
- Travel-time matrix validity depends on upstream routing assumptions and network vintage.
- Sensitivity scenarios test score robustness but do not clinically validate the score.

## Resume Instructions

Continue from the current Git worktree. Inspect `git status`, rerun the full validation gate if new
changes are made, and do not publish real facility-status claims without independent verification.
