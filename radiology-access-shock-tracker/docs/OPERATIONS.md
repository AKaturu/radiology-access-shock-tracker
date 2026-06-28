# Operations Notes

## Quarterly MQSA Source Refresh

The GitHub Actions workflow `.github/workflows/quarterly-snapshot.yml` is enabled for both manual
dispatch and the quarterly cron schedule. It fetches the FDA MQSA public ZIP, archives source
metadata, prepares a state-filtered review CSV, and uploads those review artifacts.

This workflow intentionally stops before approval, snapshot finalization, analysis, or publication.
The FDA refresh step does not require a repository secret.

## Review Owners

Before publishing real-world findings, configure branch protection or required reviewers in GitHub
for the people responsible for source review. The local repository cannot set GitHub organization
reviewers or teams without repository admin access.

Recommended protected actions:

- require review for changes to `.github/workflows/`, `src/radshock/adapters/`, and `docs/DATA_SOURCES.md`
- require review before accepting finalized facility snapshots or route matrices
- require a source-review owner before resolving readiness-audit blockers

The repository now includes `.github/CODEOWNERS`, with `@AKaturu` as the default owner
because the README points at `AKaturu/radiology-access-shock-tracker`. Update that file if
the repository owner or source-review team changes.

## GitHub Governance Setup

GitHub branch protection and repository secrets must be applied in GitHub by an authenticated repo
admin or owner. This checkout currently has no configured git remote and no authenticated GitHub CLI,
so the settings cannot be applied locally without adding those credentials.

After installing and authenticating the GitHub CLI, run a dry run:

```powershell
$env:GITHUB_REPOSITORY = "AKaturu/radiology-access-shock-tracker"
.\scripts\configure_github_governance.ps1
```

If Windows blocks local PowerShell scripts, run the same command with a process-scoped execution
policy bypass:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\configure_github_governance.ps1
```

Then set the required secret values in the current shell and apply:

```powershell
$env:CENSUS_API_KEY = "<your-census-key>"
$env:OPENROUTESERVICE_API_KEY = "<your-openrouteservice-key>"
.\scripts\configure_github_governance.ps1 -Apply
```

The script sets repository secrets from environment variables and applies
`.github/branch-protection.main.json` by default. Use
`.github/branch-protection.master.json` only if you publish the local `master` branch unchanged.
The protection template requires the `test` status check, code-owner review, stale-review
dismissal, conversation resolution, and blocks force pushes and branch deletion.

## External Credentials

Do not commit production credentials. Configure them as GitHub repository or organization secrets
when workflows start using those integrations.

Expected external credentials:

- `CENSUS_API_KEY`: required for ACS API pulls in environments where the Census API rejects keyless requests.
- `OPENROUTESERVICE_API_KEY`: required only when using hosted OpenRouteService for route-time drafts.
- Other routing provider credentials: required only after an approved road-time provider is selected and wired into a workflow.

The current quarterly FDA review-artifact workflow does not use these secrets.

Audit production configuration before scheduled or publication runs:

```bash
radshock audit-production-config config.example.toml \
  --output-csv work/production-readiness-build/production_config_audit.csv
```

The audit checks that review owners are named and required credential environment variables are
present. It never writes secret values to disk.

## Census API Key

The Census Bureau states that all Census Data API queries now require an API key. Request a key at:

<https://api.census.gov/data/key_signup.html>

After the key is issued and activated, store it locally as `CENSUS_API_KEY` or configure it as a
GitHub repository/organization secret with the same name. Do not commit the key.

Build the NC Census context CSVs:

```powershell
$env:CENSUS_API_KEY = "<your-census-key>"
radshock fetch-census-county-context `
  --output-csv data/counties.csv `
  --raw-context-csv data/census_county_context_2024.csv `
  --population-points-csv data/population_points.csv `
  --year 2024
```

The command writes county-centroid population points for testing. Build finer tract-centroid
population points before publication route review:

```powershell
radshock fetch-census-population-points `
  --output-csv data/population_points_tracts.csv `
  --raw-context-csv data/census_tract_context_2024.csv `
  --metadata-json data/census_tract_context_2024.metadata.json `
  --year 2024
```

Use `data/population_points_tracts.csv` when preparing production travel-time worklists, then
regenerate and review route matrices against that same population file. For tract-level worklists,
use a reviewed distance cap and nearest-facility cap to keep the routing set practical:

```powershell
radshock prepare-travel-time-review `
  --population-csv data/population_points_tracts.csv `
  --facilities-csv data/snapshots/2026-07-01/facilities.csv `
  --output-csv work/2026-07-01_tract_travel_time_review.csv `
  --metadata-json work/2026-07-01_tract_travel_time_review.metadata.json `
  --max-distance-miles 150 `
  --max-facilities-per-point 20
```

The nearest-facility cap is a pruning assumption, not a routing result. Keep it with the route
metadata and review whether it is broad enough for the selected provider and geography.

## Travel-Time Provider Options

For draft route review, the project supports OSRM-compatible Table API servers:

```bash
radshock fill-travel-time-review \
  work/source-refresh-smoke/travel-time/travel_time_review_real_facility_smoke.csv \
  --output-csv work/source-refresh-smoke/travel-time/travel_time_review_real_facility_smoke_osrm_draft.csv \
  --provider osrm \
  --osrm-base-url https://router.project-osrm.org
```

The public OSRM demo server has no quality or uptime guarantees and can withdraw access, so it
should not be treated as a production provider. For publication workflows, prefer a self-hosted
OSRM instance with documented OSM extract date/profile or an approved commercial provider such as
Google Routes Compute Route Matrix. Google Routes requires a Google Maps Platform project, billing,
and an API key; matrix requests are billed per origin-destination element.

For the publishable NC tract package, run the manual GitHub Actions workflow
`self-hosted OSRM travel-time package`. It downloads the Geofabrik North Carolina OSM PBF extract,
verifies the `.md5`, builds an OSRM MLD graph with the car profile, fills the tract nearest-20
route review through `http://127.0.0.1:5000`, writes a new matrix, and emits an audited analysis
package artifact.

The workflow input `osm_data_timestamp` must match the Geofabrik page line "contains all OSM data
up to ...". As of the local self-hosted OSRM pass on 2026-06-20, the North Carolina page reported
`2026-06-19T20:21:41Z`. If the page changes, update the workflow input rather than reusing the old
timestamp.

The same run can be executed on any Linux host with Docker, or from Git Bash on Windows when Docker
Desktop is using its WSL-backed Linux engine:

```bash
export OSM_DATA_TIMESTAMP="2026-06-19T20:21:41Z"
bash scripts/run_self_hosted_osrm_matrix.sh
```

The 2026-06-20 local run routed 52,680 of 52,680 tract-nearest facility pairs with zero unreachable
rows, wrote `work/self-hosted-osrm/analysis-tract-self-hosted-osrm`, and reported readiness `READY`
with zero blockers and zero warnings. If a later run does not report readiness `READY`, do not
publish the route-time findings until the blockers are resolved.

For hosted OpenRouteService testing, store the key as `OPENROUTESERVICE_API_KEY` and call:

```powershell
$env:OPENROUTESERVICE_API_KEY = "<your-openrouteservice-key>"
```

```bash
radshock fill-travel-time-review \
  work/source-refresh-smoke/travel-time/travel_time_review_real_facility_smoke.csv \
  --output-csv work/source-refresh-smoke/travel-time/travel_time_review_real_facility_smoke_ors_draft.csv \
  --provider openrouteservice \
  --ors-profile driving-car \
  --request-delay-seconds 3
```

OpenRouteService Matrix results are returned as durations in seconds and converted to minutes by
the fill command. Hosted OpenRouteService has request restrictions, including a Matrix limit based
on origin-destination pairs per request; check the provider dashboard and restrictions page before
running large batches.

If a hosted routing provider throttles a long run, rerun against the partially filled review CSV
with `--only-missing` and a higher `--request-delay-seconds` value.

Before finalization, reviewers must record or verify:

- provider and endpoint
- road network vintage or map data date
- travel mode/profile
- traffic assumption, if any
- unreachable/excluded route policy
- license/attribution requirements

Only after that review should `review_status` be changed from `needs_review` to `reviewed`,
`verified`, or `approved`, followed by `radshock finalize-travel-time-review`.

After route review, generate uncertainty and plausibility checks:

```bash
radshock route-uncertainty-check \
  work/self-hosted-osrm/2026-06-20_tract_nearest20_self_hosted_osrm_review.csv \
  --output-csv work/self-hosted-osrm/analysis-tract-self-hosted-osrm/route_uncertainty.csv
```

To prepare dashboard-readable data-quality artifacts:

```bash
radshock data-quality-report \
  --output-dir work/self-hosted-osrm/analysis-tract-self-hosted-osrm \
  --facilities-csv data/snapshots/2026-06-20/facilities.csv \
  --population-csv data/population_points_tracts.csv \
  --mqsa-review-csv work/source-refresh-smoke/review/fda_mqsa_2026-06-20_NC_review.csv \
  --travel-time-review-csv work/self-hosted-osrm/2026-06-20_tract_nearest20_self_hosted_osrm_review.csv
```

## Causal-Study Export Tables

When reviewed multi-period CMS utilization inputs are available, export descriptive study-design
tables with repeated pre/post periods:

```bash
radshock export-causal-study \
  --utilization-csv work/reviewed-cms-utilization.csv \
  --county-shocks-csv work/self-hosted-osrm/analysis-tract-self-hosted-osrm/county_shocks.csv \
  --output-dir work/causal-study-export \
  --pre-period 2024Q1 \
  --pre-period 2024Q2 \
  --post-period 2025Q1 \
  --post-period 2025Q2
```

The outputs are descriptive design tables, not causal estimates.

## Candidate-Site Review

Generate a starter candidate review sheet from county centroids:

```powershell
radshock prepare-candidate-review `
  --counties-csv data/counties.csv `
  --output-csv work/candidate_review.csv `
  --metadata-json work/candidate_review.metadata.json
```

County-centroid candidates are placeholders. Review or replace candidate rows with documented
mobile-stop or fixed-site assumptions.

To generate the reviewed HRSA service-delivery assumption sheet used by the current NC package,
archive the HRSA source and prepare the candidate review CSV:

```powershell
radshock fetch-source `
  --url "https://data.hrsa.gov/DataDownload/DD_Files/Health_Center_Service_Delivery_and_LookAlike_Sites.csv" `
  --source-name hrsa-health-center-service-delivery-sites `
  --output-dir work/source-refresh-smoke/raw `
  --retrieved-on 2026-06-20

radshock prepare-hrsa-candidate-review `
  work/source-refresh-smoke/raw/hrsa-health-center-service-delivery-sites/2026-06-20/Health_Center_Service_Delivery_and_LookAlike_Sites.csv `
  --output-csv data/candidate_sites_review.csv `
  --metadata-json data/candidate_sites_review.metadata.json `
  --state NC
```

By default the HRSA command keeps active service-delivery rows and excludes administrative-only
rows. It writes fixed-site, seasonal fixed-site, and mobile-stop planning assumptions; it does not
claim mammography capability.

Finalize only after setting `review_status` to `reviewed`, `verified`, or `approved`:

```powershell
radshock finalize-candidate-review `
  data/candidate_sites_review.csv `
  --output-csv data/candidate_sites.csv `
  --metadata-json data/candidate_sites.metadata.json
```
