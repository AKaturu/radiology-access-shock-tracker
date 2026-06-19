# Architecture

## Scope

Radiology Access Shock Tracker is a North Carolina mammography access surveillance toolkit. It
compares dated facility snapshots, estimates population-weighted access changes, prioritizes county
alerts, evaluates candidate response sites, and generates cautious reports.

## Components

- `radshock.adapters`: source-specific ingestion helpers. These normalize reviewed source files or
  mocked/live API responses into internal tables without making clinical claims.
- `radshock.schemas`: shared table contracts and validation.
- `radshock.snapshots`: immutable dated snapshot storage with checksums and provenance metadata.
- `radshock.changes`: facility-level event signal detection.
- `radshock.access`: nearest-facility access calculations and transparent shock-score components.
- `radshock.utilization`: descriptive CMS-style utilization change summaries.
- `radshock.intervention`: geographic planning simulation for candidate mobile or fixed sites.
- `radshock.briefs`: Markdown and HTML report generation.
- `radshock.cli` and `radshock.app`: user-facing automation and dashboard surfaces.

## Data Flow

1. A raw source file is downloaded or manually supplied and archived with checksum metadata.
2. FDA/MQSA fixed-width files can be converted into a human-review CSV.
3. The review CSV is finalized only after required reviewed fields and review statuses pass.
4. A reviewed facility source is normalized and validated.
5. `store_snapshot` writes a dated immutable snapshot directory with source provenance.
6. Two snapshots are compared to produce facility event signals.
7. Population points are evaluated against before and after facilities.
8. County access deltas, vulnerability context, and utilization summaries are merged.
9. Candidate response sites are ranked by geographic access recovery.
10. CSV outputs, briefs, and dashboard views expose the results with limitations.

## Failure Modes

- A disappeared facility ID can be a closure, identifier change, extraction issue, or source update.
- Great-circle distance is not road travel time.
- CMS fee-for-service utilization does not represent the full population.
- Synthetic data can resemble real geography and must remain clearly labeled.
- Live public-data schemas and API requirements can change; CI uses fixtures and mocked responses.
- FDA/MQSA public files lack coordinates and stable tracker IDs, so human review is required before
  a production snapshot can be created.
- Review CSVs with blank production fields or unapproved review statuses are blocked before
  snapshot ingestion.
