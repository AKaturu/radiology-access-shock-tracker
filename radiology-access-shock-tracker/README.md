# Radiology Access Shock Tracker

[![Tests](https://github.com/krishna2006sai/radiology-access-shock-tracker/actions/workflows/tests.yml/badge.svg)](https://github.com/krishna2006sai/radiology-access-shock-tracker/actions/workflows/tests.yml)

An open-source surveillance toolkit for detecting changes in mammography access, estimating which communities are affected, and comparing candidate response locations.

## What the MVP does

- Versions dated facility snapshots with checksums and metadata.
- Detects new listings, possible closures, relocations, status changes, renames, and capacity reductions.
- Calculates population-weighted distance, or reviewed travel time, to the nearest active facility
  before and after a change.
- Produces a vulnerability-adjusted county shock score and alert level.
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
├── analysis/
│   ├── county_shocks.csv
│   ├── facility_events.csv
│   ├── intervention_rankings.csv
│   └── utilization_change.csv
├── briefs/policy_brief.md
├── inputs/
├── snapshots/
└── manifest.json
```

## Use your own reviewed facility data

Production facility ingestion is intentionally two-stage. First archive the raw source file, then
create a review template. The FDA MQSA public file does not contain stable tracker IDs, coordinates,
active status, or capacity, so those fields must be reviewed before snapshot ingestion.

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
Human review is still required before finalization.

Complete the blank reviewed fields, set `review_status` to `reviewed`, `verified`, or `approved`,
then finalize it into a snapshot-ready CSV:

```bash
radshock finalize-mqsa-review \
  work/fda_mqsa_nc_geocoded.csv \
  --output-csv work/facilities_2026_07_reviewed.csv
```

This command fails if any row is still `needs_review` or if `facility_id`, `latitude`,
`longitude`, `annual_capacity`, or `active` is blank.

Your finalized facility CSV must contain:

```text
facility_id,facility_name,latitude,longitude,annual_capacity,active
```

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

Run the full analysis:

```bash
radshock analyze \
  --before-csv data/snapshots/2026-04-01/facilities.csv \
  --after-csv data/snapshots/2026-07-01/facilities.csv \
  --population-csv data/population_points.csv \
  --counties-csv data/counties.csv \
  --candidates-csv data/candidate_sites.csv \
  --utilization-csv data/utilization.csv \
  --output-dir outputs/2026-Q3
```

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
