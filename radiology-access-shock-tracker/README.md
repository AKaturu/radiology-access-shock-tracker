# Radiology Access Shock Tracker

[![Tests](https://github.com/krishna2006sai/radiology-access-shock-tracker/actions/workflows/tests.yml/badge.svg)](https://github.com/krishna2006sai/radiology-access-shock-tracker/actions/workflows/tests.yml)

An open-source surveillance toolkit for detecting changes in mammography access, estimating which communities are affected, and comparing candidate response locations.

## What the MVP does

- Versions dated facility snapshots with checksums and metadata.
- Detects new listings, possible closures, relocations, status changes, renames, and capacity
  reductions when reviewed capacity data are supplied.
- Calculates population-weighted distance, or reviewed travel time, to the nearest active facility
  before and after a change.
- Produces a vulnerability-adjusted county shock score and alert level.
- Re-scores county shocks under alternative weighting assumptions for sensitivity review.
- Audits analysis packages for publication-readiness blockers, warnings, and provenance gaps.
- Summarizes before/after screening utilization signals.
- Ranks hypothetical mobile mammography or fixed-site locations by geographic access recovery.
- Generates CSV outputs, a Streamlit dashboard, and a downloadable Markdown policy brief.

## Important status

The included demonstration uses **synthetic North Carolina-like data**. It must not be interpreted
as a real facility, county, screening, or utilization assessment. The default demo uses
great-circle distance; production road-time analysis requires reviewed travel-time matrix inputs.
The toolkit does not infer that facility events caused utilization changes.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
radshock demo --output-dir outputs/demo
streamlit run src/radshock/app.py
```

Then open the local Streamlit URL shown in the terminal.

## Generated outputs

```text
outputs/demo/
|-- analysis/
|   |-- county_shocks.csv
|   |-- facility_events.csv
|   |-- intervention_rankings.csv
|   |-- readiness_audit.json
|   |-- readiness_audit.md
|   |-- sensitivity_analysis.csv
|   `-- utilization_change.csv
|-- briefs/
|   |-- policy_brief.html
|   `-- policy_brief.md
|-- inputs/
|-- snapshots/
`-- manifest.json
```

The synthetic demo readiness audit is expected to be `BLOCKED`; it proves the publication gate is
working and visible in the dashboard.

## Use your own reviewed facility data

Production facility ingestion is intentionally two-stage. First archive the raw source file, then
create a review template. The FDA MQSA public file does not contain stable tracker IDs, coordinates,
active status, or facility-level annual capacity, so IDs, coordinates, and active status must be
reviewed before snapshot ingestion. Capacity is optional and should remain blank unless a reviewed
source or explicitly labeled proxy supports it.

Archive the weekly FDA MQSA public ZIP:

```bash
radshock fetch-fda-mqsa --output-dir data/raw
```

If you already downloaded the FDA ZIP manually:

```bash
radshock archive-source public.zip \
  --source-name fda-mqsa-public \
  --source-url https://www.accessdata.fda.gov/premarket/ftparea/public.zip
```

Prepare a human-review CSV:

```bash
radshock prepare-mqsa-review \
  data/raw/fda-mqsa-public/2026-07-01/public.zip \
  --output-csv work/fda_mqsa_nc_review.csv \
  --state NC
```

Optionally fill coordinate candidates from the US Census Geocoder before manual review:

```bash
radshock geocode-mqsa-review \
  work/fda_mqsa_nc_review.csv \
  --output-csv work/fda_mqsa_nc_geocoded.csv \
  --provider census \
  --cache-path data/cache/geocoding/census.json
```

Geocoding writes candidate coordinates and provenance columns, but it does not approve any row.
Human review is still required before finalization. If you supplement unmatched rows with a
manual or third-party fallback geocoder, keep the fallback provider, matched address, score or
benchmark, source URL, retrieval timestamp, and any approximate-match note in the geocode
provenance columns.

Complete the blank required reviewed fields, set `review_status` to `reviewed`, `verified`, or `approved`,
then finalize it into a snapshot-ready CSV:

```bash
radshock finalize-mqsa-review \
  work/fda_mqsa_nc_geocoded.csv \
  --output-csv work/facilities_2026_07_reviewed.csv
```

This command fails if any row is still `needs_review` or if `facility_id`, `latitude`,
`longitude`, or `active` is blank. `annual_capacity` may be blank.

Your finalized facility CSV must contain:

```text
facility_id,facility_name,latitude,longitude,active
```

An optional `annual_capacity` column is accepted. It is used only for capacity-reduction signals
when both compared snapshots contain reviewed numeric values.

Store a dated snapshot:

```bash
radshock ingest-snapshot work/facilities_2026_07_reviewed.csv \
  --as-of 2026-07-01 \
  --source-name reviewed-mqsa-export \
  --source-url https://www.accessdata.fda.gov/premarket/ftparea/public.zip \
  --raw-source-path data/raw/fda-mqsa-public/2026-07-01/public.zip
```

Validate without writing:

```bash
radshock ingest-snapshot facilities_2026_07.csv \
  --as-of 2026-07-01 \
  --source-name reviewed-mqsa-export \
  --dry-run
```

Compare two snapshots:

```bash
radshock compare-snapshots \
  --before-csv data/snapshots/2026-04-01/facilities.csv \
  --after-csv data/snapshots/2026-07-01/facilities.csv \
  --output-csv outputs/2026-Q3/facility_events.csv
```

Compare county access with reviewed road travel-time matrices:

```bash
radshock prepare-travel-time-review \
  --population-csv data/population_points.csv \
  --facilities-csv data/snapshots/2026-07-01/facilities.csv \
  --output-csv work/2026-07-01_travel_time_review.csv \
  --max-distance-miles 150
```

Fill the routing worklist with results from your reviewed routing process, set `route_status` to
`routed`, `unreachable`, or `excluded`, and set `review_status` to `reviewed`, `verified`, or
`approved`. Then finalize the matrix:

```bash
radshock finalize-travel-time-review \
  work/2026-07-01_travel_time_review.csv \
  --output-csv data/travel_times/2026-07-01_point_facility.csv
```

For an OSRM-compatible routing server, you can draft route minutes before review:

```bash
radshock fill-travel-time-review \
  work/2026-07-01_travel_time_review.csv \
  --output-csv work/2026-07-01_travel_time_review_osrm_draft.csv \
  --provider osrm \
  --osrm-base-url https://router.project-osrm.org
```

For OpenRouteService testing, set the API key in the environment and use the Matrix endpoint:

```bash
export OPENROUTESERVICE_API_KEY="..."
radshock fill-travel-time-review \
  work/2026-07-01_travel_time_review.csv \
  --output-csv work/2026-07-01_travel_time_review_ors_draft.csv \
  --provider openrouteservice \
  --ors-profile driving-car
```

The fill command keeps `review_status=needs_review` by default. Do not finalize the matrix until
the routing provider, network vintage, traffic assumptions, provider terms, and row-level outputs
have been reviewed.

```bash
radshock compare-travel-time-access \
  --before-csv data/snapshots/2026-04-01/facilities.csv \
  --after-csv data/snapshots/2026-07-01/facilities.csv \
  --population-csv data/population_points.csv \
  --counties-csv data/counties.csv \
  --before-travel-times-csv data/travel_times/2026-04-01_point_facility.csv \
  --after-travel-times-csv data/travel_times/2026-07-01_point_facility.csv \
  --output-csv outputs/2026-Q3/county_travel_time_shocks.csv
```

Travel-time matrices must contain `point_id`, `facility_id`, and `travel_time_minutes`.
Duplicate point/facility pairs and negative travel times are rejected.

Run shock-score sensitivity analysis:

```bash
radshock sensitivity-analysis \
  outputs/2026-Q3/county_shocks.csv \
  --output-csv outputs/2026-Q3/sensitivity_analysis.csv
```

The sensitivity output keeps the baseline score and rank next to each alternative scenario. It is a
review aid, not a validated clinical or policy threshold.

Audit production readiness before sharing real-world findings. `radshock analyze` writes an initial
manifest and readiness audit into its output directory; rerun the audit with explicit snapshot and
raw-source metadata before publication review:

```bash
radshock readiness-audit \
  --analysis-dir outputs/2026-Q3 \
  --before-snapshot-dir data/snapshots/2026-04-01 \
  --after-snapshot-dir data/snapshots/2026-07-01 \
  --raw-source-metadata data/raw/fda-mqsa-public/2026-07-01/public.zip.metadata.json \
  --output-json outputs/2026-Q3/readiness_audit.json \
  --output-md outputs/2026-Q3/readiness_audit.md
```

The audit blocks synthetic manifests, unresolved facility-event verification, missing core outputs,
bad snapshot checksums, and missing required production artifacts.

Run the full analysis:

```bash
radshock analyze \
  --before-csv data/snapshots/2026-04-01/facilities.csv \
  --after-csv data/snapshots/2026-07-01/facilities.csv \
  --population-csv data/population_points.csv \
  --counties-csv data/counties.csv \
  --candidates-csv data/candidate_sites.csv \
  --utilization-csv data/utilization.csv \
  --raw-source-metadata data/raw/fda-mqsa-public/2026-07-01/public.zip.metadata.json \
  --output-dir outputs/2026-Q3
```

The analysis command writes CSV outputs, `manifest.json`, `readiness_audit.json`,
`readiness_audit.md`, and policy briefs. If the before/after CSVs are stored snapshot
`facilities.csv` files, snapshot directories are inferred for the readiness audit.

## Automation

The `quarterly MQSA source refresh` GitHub Actions workflow can be run manually to fetch the FDA
MQSA public ZIP, archive source metadata, and upload a state-filtered review CSV artifact. Scheduled
runs are enabled on the quarterly cron in `.github/workflows/quarterly-snapshot.yml`.

The workflow stops at the review artifact. It does not approve rows, finalize a snapshot, run a
public analysis, or publish findings.

Operational owner and credential notes are tracked in `docs/OPERATIONS.md`. The FDA source-refresh
workflow does not require a secret. Production ACS context and road-time routing need approved
external credentials before publication workflows can use those data.

## Public-data integration approach

The MVP deliberately separates source ingestion from the surveillance engine:

- `radshock.adapters.acs` fetches selected ACS 5-year county indicators.
- `radshock.adapters.places` fetches the CDC PLACES county mammography measure.
- `radshock.adapters.facilities` normalizes reviewed facility exports into the snapshot schema.
- `radshock.adapters.cms` summarizes user-downloaded provider/service extracts after explicit source-column mapping.

Facility changes are **signals requiring verification**, not definitive claims. A facility can disappear because of identifier, geocoding, naming, or source-publication changes. Disappearances are labeled `POSSIBLE_CLOSURE`, not confirmed closure.

## Methodology

See [`docs/METHODS.md`](docs/METHODS.md) for formulas, assumptions, alert thresholds, and known limitations.

## Development

```bash
pytest
ruff check .
mypy src/radshock
```

## Project boundary

The initial application remains focused on mammography access shocks. Diagnostic-resolution access, multimodality screening, workforce vulnerability, and advanced equity-constrained optimization are intentionally reserved for future applications; see [`docs/ROADMAP.md`](docs/ROADMAP.md).

## License

MIT. Public-source datasets remain governed by their respective source terms and attribution requirements.
