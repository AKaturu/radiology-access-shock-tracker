# Radiology Access Shock Tracker

[![Tests](https://github.com/AKaturu/radiology-access-shock-tracker/actions/workflows/tests.yml/badge.svg)](https://github.com/AKaturu/radiology-access-shock-tracker/actions/workflows/tests.yml)

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

The `radshock demo` command still creates **synthetic North Carolina-like data** and must not be
interpreted as a real facility, county, screening, or utilization assessment. The published
dashboard preview assets below intentionally use the synthetic demo so the public project is easy
to run and review. Reviewed real-data packages are documented separately and should be used only
with the publication-readiness caveats in the validation report.

## Dashboard preview

![Dashboard overview](docs/assets/github/dashboard-overview.png)

More screenshots and walkthrough footage are in [`docs/GITHUB_PAGE_ASSETS.md`](docs/GITHUB_PAGE_ASSETS.md).
The latest compiled local validation summary is in
[`docs/validation/COMPILED_TEST_REPORT.md`](docs/validation/COMPILED_TEST_REPORT.md).
Publishing instructions are in [`docs/GITHUB_PUBLISHING.md`](docs/GITHUB_PUBLISHING.md). Journal
write-up packaging notes and a ChatGPT drafting prompt are in
[`docs/JOURNAL_REPORT_PACKAGE.md`](docs/JOURNAL_REPORT_PACKAGE.md). Desktop download build
instructions are in [`docs/DESKTOP_RELEASES.md`](docs/DESKTOP_RELEASES.md).

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

## Use the reviewed real-data package

The repository also preserves a reviewed real North Carolina no-observed-change validation package.
Use it when you want to reproduce the research workflow rather than the public demo:

```bash
RADSHOCK_ANALYSIS_DIR=desktop_payload/analysis streamlit run src/radshock/app.py
```

On Windows PowerShell:

```powershell
$env:RADSHOCK_ANALYSIS_DIR = "desktop_payload/analysis"
streamlit run src/radshock/app.py
```

The reviewed real package supports workflow and methods claims, but it does not support trend,
deterioration, or causal utilization claims.

## Use your own reviewed facility data

Production facility ingestion is intentionally two-stage. First archive the raw source file, then
create a review template. The FDA MQSA public file does not contain stable tracker IDs, coordinates,
active status, or facility-level annual capacity, so IDs, coordinates, and active status must be
reviewed before snapshot ingestion. Capacity is optional and should remain blank unless a reviewed
source or explicitly labeled proxy supports it.

Archive the weekly FDA MQSA public ZIP:

```bash
radshock fetch-fda-mqsa --output-dir data/raw --retrieved-on 2026-07-01
```

If you already downloaded the FDA ZIP manually:

```bash
radshock archive-source public.zip \
  --source-name fda-mqsa-public \
  --source-url https://www.accessdata.fda.gov/premarket/ftparea/public.zip \
  --retrieved-on 2026-07-01
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

For a later FDA pull, carry forward already reviewed rows only when the raw source row is unchanged:

```bash
radshock carry-forward-mqsa-review \
  work/fda_mqsa_2026-07-01_nc_review_template.csv \
  --previous-review-csv work/facilities_2026-06-01_reviewed.csv \
  --output-csv work/fda_mqsa_2026-07-01_nc_review.csv \
  --metadata-json work/fda_mqsa_2026-07-01_nc_review.metadata.json
```

Rows with new or changed `source_record_hash` values remain `needs_review`.

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

Fetch the Census county context inputs used by the analysis:

```bash
export CENSUS_API_KEY="..."
radshock fetch-census-county-context \
  --output-csv data/counties.csv \
  --raw-context-csv data/census_county_context_2024.csv \
  --population-points-csv data/population_points.csv \
  --year 2024
```

This writes analysis-ready county context plus county-centroid population points. The centroid
points are useful for testing and smoke runs. Build finer tract-centroid population points before
publication route review:

```bash
radshock fetch-census-population-points \
  --output-csv data/population_points_tracts.csv \
  --raw-context-csv data/census_tract_context_2024.csv \
  --metadata-json data/census_tract_context_2024.metadata.json \
  --year 2024
```

Tract points are still centroid approximations, but they are the preferred built-in public-data
input for production review.

```bash
radshock prepare-travel-time-review \
  --population-csv data/population_points_tracts.csv \
  --facilities-csv data/snapshots/2026-07-01/facilities.csv \
  --output-csv work/2026-07-01_travel_time_review.csv \
  --metadata-json work/2026-07-01_travel_time_review.metadata.json \
  --max-distance-miles 150 \
  --max-facilities-per-point 20
```

Fill the routing worklist with results from your reviewed routing process, set `route_status` to
`routed`, `unreachable`, or `excluded`, and set `review_status` to `reviewed`, `verified`, or
`approved`. Then finalize the matrix:

```bash
radshock finalize-travel-time-review \
  work/2026-07-01_travel_time_review.csv \
  --output-csv data/travel_times/2026-07-01_point_facility.csv \
  --metadata-json data/travel_times/2026-07-01_point_facility.metadata.json
```

For an OSRM-compatible routing server, you can draft route minutes before review:

```bash
radshock fill-travel-time-review \
  work/2026-07-01_travel_time_review.csv \
  --output-csv work/2026-07-01_travel_time_review_osrm_draft.csv \
  --provider osrm \
  --osrm-base-url https://router.project-osrm.org \
  --only-missing \
  --max-origins 100
```

For publication-grade NC road-time outputs, use the manual GitHub Actions workflow
`self-hosted OSRM travel-time package` or run the same script on a Linux host with Docker. The
script also supports Git Bash on Windows when Docker Desktop is using its WSL-backed Linux engine:

```bash
export OSM_DATA_TIMESTAMP="2026-06-19T20:21:41Z"
bash scripts/run_self_hosted_osrm_matrix.sh
```

That path builds a local OSRM graph from the Geofabrik North Carolina extract, routes through
`127.0.0.1`, records map extract/profile/traffic-assumption provenance, and reruns the readiness
audit. Do not publish road-time findings unless that package reports readiness `READY`.

For OpenRouteService testing, set the API key in the environment and use the Matrix endpoint:

```bash
export OPENROUTESERVICE_API_KEY="..."
radshock fill-travel-time-review \
  work/2026-07-01_travel_time_review.csv \
  --output-csv work/2026-07-01_travel_time_review_ors_draft.csv \
  --provider openrouteservice \
  --ors-profile driving-car \
  --request-delay-seconds 3 \
  --only-missing \
  --max-origins 50
```

The fill command keeps `review_status=needs_review` by default. Do not finalize the matrix until
the routing provider, network vintage, traffic assumptions, provider terms, and row-level outputs
have been reviewed.

```bash
radshock compare-travel-time-access \
  --before-csv data/snapshots/2026-04-01/facilities.csv \
  --after-csv data/snapshots/2026-07-01/facilities.csv \
  --population-csv data/population_points_tracts.csv \
  --counties-csv data/counties.csv \
  --before-travel-times-csv data/travel_times/2026-04-01_point_facility.csv \
  --after-travel-times-csv data/travel_times/2026-07-01_point_facility.csv \
  --output-csv outputs/2026-Q3/county_travel_time_shocks.csv
```

Travel-time matrices must contain `point_id`, `facility_id`, and `travel_time_minutes`.
Duplicate point/facility pairs and negative travel times are rejected.
If `--max-facilities-per-point` is used to limit routing volume, record and review that pruning
assumption with the route provider metadata before publication.

Prepare candidate response sites through a review gate before using intervention rankings:

```bash
radshock prepare-candidate-review \
  --counties-csv data/counties.csv \
  --output-csv work/candidate_review.csv \
  --metadata-json work/candidate_review.metadata.json
```

The generated county-centroid candidates are placeholders. Prefer a documented real-source
candidate sheet before operational use. The current NC package uses HRSA Health Center Program
Service Delivery and Look-Alike Sites as active service-delivery planning assumptions:

```bash
radshock fetch-source \
  --url https://data.hrsa.gov/DataDownload/DD_Files/Health_Center_Service_Delivery_and_LookAlike_Sites.csv \
  --source-name hrsa-health-center-service-delivery-sites \
  --output-dir data/raw

radshock prepare-hrsa-candidate-review \
  data/raw/hrsa-health-center-service-delivery-sites/2026-06-20/Health_Center_Service_Delivery_and_LookAlike_Sites.csv \
  --output-csv work/hrsa_candidate_review.csv \
  --metadata-json work/hrsa_candidate_review.metadata.json
```

HRSA rows are real health-center service delivery sites, but candidate rows are still planning
assumptions and are not claims that the sites provide mammography. Review the assumptions, set
`review_status` to `reviewed`, `verified`, or `approved`, then finalize:

```bash
radshock finalize-candidate-review \
  work/hrsa_candidate_review.csv \
  --output-csv data/candidate_sites.csv \
  --metadata-json data/candidate_sites.metadata.json
```

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
When road-time outputs are required, it also blocks missing route-provider provenance and
testing-grade public OSRM route matrices. Candidate rankings based on county-centroid placeholders
are warned until replaced with reviewed mobile-stop or fixed-site assumptions.

Run the full analysis:

```bash
radshock analyze \
  --before-csv data/snapshots/2026-04-01/facilities.csv \
  --after-csv data/snapshots/2026-07-01/facilities.csv \
  --population-csv data/population_points_tracts.csv \
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

Repository governance lives in `.github/CODEOWNERS`, `.github/branch-protection.main.json`,
`.github/branch-protection.master.json`, and `scripts/configure_github_governance.ps1`. A GitHub
repo admin can run the script with authenticated `gh` to set `CENSUS_API_KEY`,
`OPENROUTESERVICE_API_KEY`, required code-owner review, branch protection, and the `test` status
check requirement. See `docs/OPERATIONS.md` for the exact setup flow.

Operational owner and credential notes are tracked in `docs/OPERATIONS.md`. The FDA source-refresh
workflow does not require a secret. Production ACS context and road-time routing need approved
external credentials before publication workflows can use those data.

## Public-data integration approach

The MVP deliberately separates source ingestion from the surveillance engine:

- `radshock.adapters.acs` fetches selected ACS 5-year county and tract indicators.
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
