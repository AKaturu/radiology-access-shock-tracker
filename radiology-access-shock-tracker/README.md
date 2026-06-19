# Radiology Access Shock Tracker

[![Tests](https://github.com/krishna2006sai/radiology-access-shock-tracker/actions/workflows/tests.yml/badge.svg)](https://github.com/krishna2006sai/radiology-access-shock-tracker/actions/workflows/tests.yml)

An open-source surveillance toolkit for detecting changes in mammography access, estimating which communities are affected, and comparing candidate response locations.

## What the MVP does

- Versions dated facility snapshots with checksums and metadata.
- Detects possible openings, closures, relocations, status changes, renames, and capacity reductions.
- Calculates population-weighted distance to the nearest active facility before and after a change.
- Produces a vulnerability-adjusted county shock score and alert level.
- Summarizes before/after screening utilization signals.
- Ranks hypothetical mobile mammography or fixed-site locations by geographic access recovery.
- Generates CSV outputs, a Streamlit dashboard, and a downloadable Markdown policy brief.

## Important status

The included demonstration uses **synthetic North Carolina-like data**. It must not be interpreted as a real facility, county, screening, or utilization assessment. The MVP uses great-circle distance rather than road-network travel time and does not infer that facility events caused utilization changes.

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

Your facility CSV must contain:

```text
facility_id,facility_name,latitude,longitude,annual_capacity,active
```

Store a dated snapshot:

```bash
radshock ingest-snapshot facilities_2026_07.csv \
  --as-of 2026-07-01 \
  --source-name reviewed-mqsa-export
```

Compare two snapshots:

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

Facility changes are **signals requiring verification**, not definitive claims. A facility can disappear because of identifier, geocoding, naming, or source-publication changes.

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
