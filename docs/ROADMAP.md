# Roadmap

## MVP: access-shock surveillance

- North Carolina mammography facility snapshots
- new listings, possible closures, relocations, and possible service reductions
- population-weighted geographic access change
- vulnerability-adjusted county alerts
- CMS screening utilization signal
- mobile/fixed candidate response ranking
- reproducible policy brief generation

## Production readiness status

1. First reviewed FDA/MQSA snapshot: complete for the promoted 2026-06-19 and 2026-06-20 North
   Carolina snapshots, with carry-forward review documented for unchanged FDA source rows.
2. Census-derived small-area population points: complete for 2024 ACS 5-year tract-centroid
   population points weighted by female population age 50-74.
3. Reviewed road-network travel-time matrices: complete for the self-hosted OSRM tract-nearest
   matrix; `route-uncertainty-check` now summarizes coverage, route metadata, and plausibility
   flags for reviewer signoff.
4. Source review owners and production credentials: `config.example.toml` now declares review
   owners and required credential environment variables; `audit-production-config` checks local
   or GitHub-runner readiness without printing secret values.
5. Multiple pre/post CMS periods and causal-study exports: `export-causal-study` now writes
   descriptive county and period panels for repeated pre/post periods. Real causal exports still
   require reviewed multi-period CMS utilization inputs.
6. Data-quality dashboards, geocoder confidence, and identifier crosswalks: `data-quality-report`
   writes `data_quality.csv`, `geocoder_confidence.csv`, `identifier_crosswalk.csv`, and optional
   `route_uncertainty.csv`; the Streamlit dashboard displays them when present.
7. Sensitivity-analysis reports beyond CSV: `sensitivity-analysis` and `analyze` now generate
   Markdown and HTML sensitivity review reports in addition to CSV outputs.

## Reserved future applications

The following are intentionally outside the first application so they can become distinct future research and software projects:

- diagnostic-resolution access after an abnormal screen;
- multimodality screening access, including low-dose CT;
- advanced equity-constrained facility or mobile-route optimization;
- radiology workforce vulnerability and provider-loss simulation.
