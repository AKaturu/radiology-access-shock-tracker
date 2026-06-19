# Architecture

## Scope

Radiology Access Shock Tracker is a North Carolina mammography access surveillance toolkit. It
compares dated facility snapshots, estimates population-weighted access changes, prioritizes county
alerts, evaluates candidate response sites, and generates cautious reports.

## Components

- `radshock.adapters`: source-specific ingestion helpers. These normalize reviewed source files or
  mocked/live API responses into internal tables without making clinical claims.
- `radshock.geocoding`: optional provider and cache layer for filling MQSA review coordinate
  candidates with provenance before human approval.
- `radshock.schemas`: shared table contracts and validation.
- `radshock.snapshots`: immutable dated snapshot storage with checksums and provenance metadata.
- `radshock.changes`: facility-level event signal detection.
- `radshock.access`: nearest-facility distance and reviewed travel-time access calculations with
  transparent shock-score components.
- `radshock.sensitivity`: post-processing sensitivity analysis for alternate shock-score weights
  and rank movement.
- `radshock.utilization`: descriptive CMS-style utilization change summaries.
- `radshock.intervention`: geographic planning simulation for candidate mobile or fixed sites.
- `radshock.briefs`: Markdown and HTML report generation.
- `radshock.cli` and `radshock.app`: user-facing automation and dashboard surfaces.

## Data Flow

1. A raw source file is downloaded or manually supplied and archived with checksum metadata.
2. FDA/MQSA fixed-width files can be converted into a human-review CSV.
3. Optional geocoding fills candidate coordinates and provenance in the review CSV.
4. The review CSV is finalized only after required reviewed fields and review statuses pass.
5. A reviewed facility source is normalized and validated.
6. `store_snapshot` writes a dated immutable snapshot directory with source provenance.
7. Two snapshots are compared to produce facility event signals.
8. Population points are evaluated against before and after facilities using distance or a reviewed
   point-to-facility travel-time matrix.
9. County access deltas, vulnerability context, and utilization summaries are merged.
10. Sensitivity analysis re-scores county shocks under alternate transparent weighting assumptions.
11. Candidate response sites are ranked by geographic access recovery.
12. CSV outputs, briefs, and dashboard views expose the results with limitations.

## Failure Modes

- A disappeared facility ID can be a closure, identifier change, extraction issue, or source update.
- Great-circle distance is not road travel time.
- Travel-time matrices can be incomplete or generated with unsuitable routing assumptions; route
  coverage and provenance must be reviewed before publication.
- CMS fee-for-service utilization does not represent the full population.
- Synthetic data can resemble real geography and must remain clearly labeled.
- Live public-data schemas and API requirements can change; CI uses fixtures and mocked responses.
- FDA/MQSA public files lack coordinates and stable tracker IDs, so human review is required before
  a production snapshot can be created.
- Geocoder matches can be ambiguous, stale, or incorrect; candidate coordinates cannot bypass the
  review-status gate.
- Review CSVs with blank production fields or unapproved review statuses are blocked before
  snapshot ingestion.
- Sensitivity scenarios reveal score/rank instability but do not validate the exploratory score.
