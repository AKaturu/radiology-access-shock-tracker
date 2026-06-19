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
gates, cached geocoding assistance, docs, and tests.

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

## Current Work

### Active Feature

Production readiness hardening.

### Progress

Latest validation gate completed:

- `python -m pytest` passed with 27 tests.
- `python -m ruff check .` passed.
- `python -m mypy src/radshock` passed.
- `python -m pip wheel . -w work/dist` built the package wheel.
- `radshock demo --output-dir work/demo-smoke` regenerated demo outputs.
- Streamlit startup smoke test returned HTTP 200 on `127.0.0.1:8766`.

### Remaining Work

- Complete road-network travel-time backend design and implementation.
- Use a real FDA MQSA ZIP to generate the first fully reviewed NC facility CSV.
- Add sensitivity-analysis reports for alternative shock-score weights.
- Add scheduled workflow templates only after repository secrets and source review are configured.

## Next Actions

1. Review and approve the first real MQSA-derived NC facility CSV.
2. Design the road-network travel-time backend and compare outputs against great-circle distance.
3. Add sensitivity-analysis reporting for alternative shock-score weights.

## Risks

### Open Questions

- Which reviewed FDA/MQSA export format will be used for the first real snapshot?
- Which road-time backend should be approved for production use?

### Known Issues

- Live FDA, CDC, Census geocoding, and CMS integrations were not all end-to-end verified against
  live endpoints in CI.
- Great-circle distance remains the default method.

### Technical Concerns

- ACS Census API queries require an API key under current official documentation.
- CMS and public-data schemas can change by release, so fixture tests must be maintained.
- Geocoder matches can be ambiguous and must remain subject to manual review.

## Resume Instructions

Continue from the current Git worktree. Inspect `git status`, rerun the full validation gate if new
changes are made, and do not publish real facility-status claims without independent verification.
