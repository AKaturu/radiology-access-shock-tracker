# PROJECT_STATE

## Project Overview

### Project Name

Radiology Access Shock Tracker

### Goal

Create a rigorous, reproducible North Carolina mammography access-shock surveillance project that
uses synthetic data safely for demos and supports reviewed public-data ingestion paths.

### Current Status

The downloaded MVP has been committed as a baseline. The project now has safer event semantics,
score transparency, adapter validation, reports, CLI behavior, docs, and tests. Current work is
adding production source archiving and FDA/MQSA review-template creation.

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

## Current Work

### Active Feature

Production source ingestion groundwork.

### Progress

Implementation is in progress. Full validation must be rerun before release or publication.

### Remaining Work

- Complete road-network travel-time backend design and implementation.
- Use a real FDA MQSA ZIP to generate the first reviewed NC facility CSV.
- Add sensitivity-analysis reports for alternative shock-score weights.
- Add scheduled workflow templates only after repository secrets and source review are configured.

## Next Actions

1. Run pytest, Ruff, mypy, package build, CLI demo, and Streamlit smoke test.
2. Inspect diffs and generated demo outputs.
3. Commit the source-ingestion groundwork if validation passes.

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
