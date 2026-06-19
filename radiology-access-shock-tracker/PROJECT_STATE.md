# PROJECT_STATE

## Project Overview

### Project Name

Radiology Access Shock Tracker

### Goal

Create a rigorous, reproducible North Carolina mammography access-shock surveillance project that
uses synthetic data safely for demos and supports reviewed public-data ingestion paths.

### Current Status

The downloaded MVP has been committed as a baseline. This session is hardening event semantics,
score transparency, adapter validation, reports, CLI behavior, docs, and tests.

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

## Current Work

### Active Feature

Release-readiness hardening for the synthetic-data MVP.

### Progress

Implementation is in progress. Full validation must be rerun before release or publication.

### Remaining Work

- Complete road-network travel-time backend design and implementation.
- Add source-specific live data acquisition workflows with human review.
- Add sensitivity-analysis reports for alternative shock-score weights.
- Add scheduled workflow templates only after repository secrets and source review are configured.

## Next Actions

1. Run pytest, Ruff, mypy, package build, CLI demo, and Streamlit smoke test.
2. Inspect diffs and generated demo outputs.
3. Commit the hardening changes if validation passes.

## Risks

### Open Questions

- Which reviewed FDA/MQSA export format will be used for the first real snapshot?
- Which geocoder and road-time backend should be approved for production use?

### Known Issues

- Live FDA, CDC, Census, and CMS integrations were not end-to-end verified against live endpoints.
- Great-circle distance remains the default method.

### Technical Concerns

- Census API queries require an API key under current official documentation.
- CMS and public-data schemas can change by release, so fixture tests must be maintained.

## Resume Instructions

Continue from the current Git worktree. First run the full validation gate, then inspect
`git diff` and generated `work/demo-smoke` outputs. Do not publish real facility-status claims
without independent verification.
