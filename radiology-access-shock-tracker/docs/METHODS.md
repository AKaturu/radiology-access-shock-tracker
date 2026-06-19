# Methods

## 1. Facility change detection

Snapshots are keyed by a stable `facility_id` supplied by the ingestion process.

- `OPENED`: ID appears only in the later snapshot.
- `CLOSED`: ID appears only in the earlier snapshot.
- `SERVICE_LOSS`: active status changes from true to false.
- `REACTIVATED`: active status changes from false to true.
- `RELOCATED`: coordinates move by at least the configured threshold, one mile by default.
- `SERVICE_REDUCTION`: annual capacity falls by at least 25% by default.
- `RENAMED`: normalized names differ while the ID remains stable.

Every event is a surveillance signal requiring source verification. Probabilistic entity matching is intentionally deferred because false matches can create misleading closure or relocation claims.

## 2. Geographic access

For each population point, the engine calculates great-circle distance to every active facility and selects the minimum. County summaries use point weights:

- weighted mean nearest-facility distance;
- weighted 90th-percentile nearest-facility distance;
- weighted percentage farther than a configurable threshold, 30 miles by default.

Population points can represent census-block-group centroids, gridded population cells, or another reviewed small-area representation. County centroids alone are not recommended for research-grade results.

## 3. Shock score

Only worsening access contributes to the deterioration component:

```text
D = 0.45 × min(max(mean-distance change, 0) / 20, 1)
  + 0.30 × min(max(p90-distance change, 0) / 30, 1)
  + 0.25 × min(max(threshold-population change, 0) / 0.40, 1)
```

Community vulnerability is:

```text
V = 0.40 × min(poverty percentage / 30, 1)
  + 0.30 × rurality index
  + 0.30 × high-risk index
```

The exploratory score is:

```text
Shock score = 100 × D × (0.70 + 0.30 × V)
```

Alert levels:

- `NONE`: 0–5
- `WATCH`: >5–20
- `WARNING`: >20–40
- `CRITICAL`: >40

These thresholds and weights are policy-design choices, not clinically validated cutoffs. Sensitivity analysis is required before real-world deployment.

## 4. Utilization signal

The MVP calculates services per 1,000 eligible beneficiaries for two specified periods. A negative change near an access shock is descriptive and does not establish causality. A future study should use multiple pre/post periods, comparison communities, uncertainty estimates, and an appropriate quasi-experimental design.

## 5. Intervention simulation

Each candidate is temporarily treated as an unconstrained facility. The engine calculates:

- population-weighted mean distance reduction;
- total population-weighted person-miles reduced;
- population brought within the distance threshold;
- population receiving any meaningful improvement.

Candidate ranking combines normalized person-miles reduction (65%) and threshold recovery (35%). Capacity, route schedules, operating cost, referral networks, and road travel time are not yet modeled.

## 6. Reproducibility

Each snapshot directory contains the normalized CSV, analysis date, source label, record counts, creation time, and SHA-256 checksum. Production use should also archive the original source file, extraction code version, geocoder version, and manual adjudication log.
