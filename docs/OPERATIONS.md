# Operations Notes

## Quarterly MQSA Source Refresh

The GitHub Actions workflow `.github/workflows/quarterly-snapshot.yml` is enabled for both manual
dispatch and the quarterly cron schedule. It fetches the FDA MQSA public ZIP, archives source
metadata, prepares a state-filtered review CSV, and uploads those review artifacts. Manual runs can
use a two-letter state/DC abbreviation, a state/DC FIPS code, or `ALL` for a
51-jurisdiction MQSA review worklist.

This workflow intentionally stops before approval, snapshot finalization, analysis, or publication.
The FDA refresh step does not require a repository secret.

The workflow now monitors source freshness and failures:

- If the fetched FDA MQSA ZIP SHA-256 differs from the latest tracked
  `data/source_metadata/fda-mqsa-public-*.metadata.json` baseline, it opens a GitHub issue with the
  workflow run, current hash, baseline hash, and review-artifact path.
- If the refresh workflow fails, it opens a GitHub issue with the run URL and required source/parser
  follow-up.
- Source-change issue titles include the current source-hash prefix, so repeated runs for the same
  source hash reuse the existing review thread instead of opening duplicates.
- New snapshots remain blocked until the generated MQSA review CSV has completed review statuses,
  coordinates, active flags, and provenance.

Use the GitHub issue template `.github/ISSUE_TEMPLATE/data_refresh_review.yml` when creating manual
refresh-review issues outside the scheduled workflow.

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
admin or owner. In the maintained repository, `main` is protected and repository auto-merge is
enabled. Re-run the helper script after changing the branch-protection JSON templates.

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
The protection template requires the `test` and `release-package` status checks, conversation
resolution, and blocks force pushes and branch deletion. The `release-package` check regenerates
the source ZIP and journal bundle, then verifies manifest paths, byte counts, and SHA-256 hashes.

## Supply-Chain Automation

Dependabot is configured for Python dependencies and GitHub Actions. Reusable GitHub Actions are
pinned to full-length commit SHAs with version comments so workflow execution does not depend on
mutable tags. CodeQL runs on pushes, pull requests, and a weekly schedule.

Future desktop releases publish checksum companion files and
`radiology-access-shock-tracker-sbom.cdx.json`, a CycloneDX direct-dependency SBOM generated from
`pyproject.toml`. The SBOM records declared runtime, development, and desktop build dependencies;
it does not enumerate transitive dependencies installed by pip.

Use `.github/ISSUE_TEMPLATE/release_trust.yml` for each public desktop release to record checksum,
SBOM, code-signing, and macOS notarization status. Current builds publish checksums and SBOMs, but
remain unsigned until signing certificates and Apple notarization credentials are available.

## External Credentials

Do not commit production credentials. Configure them as GitHub repository or organization secrets
when workflows start using those integrations.

Expected external credentials:

- `CENSUS_API_KEY`: required for ACS API pulls in environments where the Census API rejects keyless requests.
- `OPENROUTESERVICE_API_KEY`: required only when using hosted OpenRouteService for route-time drafts.
- Other routing provider credentials: required only after an approved road-time provider is selected and wired into a workflow.

The current quarterly FDA review-artifact workflow does not use these secrets.

## Census API Key

The Census Bureau states that all Census Data API queries now require an API key. Request a key at:

<https://api.census.gov/data/key_signup.html>

After the key is issued and activated, store it locally as `CENSUS_API_KEY` or configure it as a
GitHub repository/organization secret with the same name. Do not commit the key.

```powershell
$env:CENSUS_API_KEY = "<your-census-key>"
gh secret set CENSUS_API_KEY --repo AKaturu/radiology-access-shock-tracker --body $env:CENSUS_API_KEY
```

Build Census context CSVs for the reviewed NC package:

```powershell
$env:CENSUS_API_KEY = "<your-census-key>"
radshock fetch-census-county-context `
  --output-csv data/counties.csv `
  --raw-context-csv data/census_county_context_2024.csv `
  --population-points-csv data/population_points.csv `
  --state NC `
  --year 2024
```

Use `--state ALL` to generate 51-jurisdiction county context and county-centroid population points
for review, preferably into separate output paths until the national package has been reviewed:

```powershell
radshock fetch-census-county-context `
  --output-csv work/all-states/counties.csv `
  --raw-context-csv work/all-states/census_county_context_2024.csv `
  --population-points-csv work/all-states/population_points.csv `
  --metadata-json work/all-states/census_county_context_2024.metadata.json `
  --state ALL `
  --year 2024
```

To gather the 51-jurisdiction package with ACS county and tract context in one reproducible production
prep run, use:

```powershell
python scripts/build_all_states_data_package.py `
  --output-dir work/all-states/2026-07-02 `
  --public-report outputs/all_states_data_package.md `
  --force
```

This collects FDA MQSA, HRSA candidate-source rows, CDC PLACES mammography rows, CDC/ATSDR SVI
county vulnerability context, and Census county and tract Gazetteer context for all 51 jurisdictions. If
`CENSUS_API_KEY` is not set, the command fails before producing a production-prep package. For a
staging-only package that documents missing ACS instead of blocking, pass `--allow-missing-acs`.

The GitHub Actions workflow `.github/workflows/all-states-data-package.yml` runs the same
ACS-required rebuild from `secrets.CENSUS_API_KEY` and uploads the raw, review, context, summary, and
public-report artifacts:

```powershell
gh workflow run all-states-data-package.yml `
  --repo AKaturu/radiology-access-shock-tracker `
  -f acs_year=2024
```

The generated `summary/data_package_manifest.json` includes `state_coverage` counts and
`state_coverage_gaps` lists for each source. Treat any public no-secret gap as a refresh or source
review blocker before using the package for state comparisons. The generated
`summary/state_readiness_gates.csv` lists each state's MQSA review, HRSA candidate-review,
geocoding, routing, ACS, and publication gates so non-NC findings stay blocked until each state's
human review and readiness audit are complete.

To combine owner, credential, all-state package, ACS, publication-gate, and analysis-readiness
checks into one production completion report, run:

```powershell
radshock production-audit `
  --config-path config.example.toml `
  --all-states-manifest work/all-states/2026-07-02/summary/data_package_manifest.json `
  --readiness-json desktop_payload/analysis/readiness_audit.json `
  --output-json outputs/production_audit.json `
  --output-md outputs/production_audit.md `
  --force
```

The command reports `BLOCKED` until the all-state package has ACS context when required, no
manifest readiness gates, a publication-ready package status, and a `READY` analysis readiness
report.

For production data-quality review, generate single-file reports or a review bundle:

```powershell
radshock data-quality-report data/snapshots/2026-06-20/facilities.csv `
  --dataset-type facilities `
  --output-json outputs/facilities_quality.json `
  --output-md outputs/facilities_quality.md `
  --force

radshock data-quality-report `
  --output-dir outputs/data_quality `
  --facilities-csv data/snapshots/2026-06-20/facilities.csv `
  --population-csv data/population_points_tracts.csv `
  --mqsa-review-csv work/mqsa_review.csv `
  --travel-time-review-csv data/travel_times/2026-06-20_tract_nearest20_osrm_review.csv `
  --force
```

The bundle emits `data_quality.csv`, `geocoder_confidence.csv`, `identifier_crosswalk.csv`, and
`route_uncertainty.csv` when the corresponding inputs are supplied. Use
`radshock route-uncertainty-check` for a route-review-only plausibility report.

The command writes county-centroid population points for testing. Build finer tract-centroid
population points before publication route review:

```powershell
radshock fetch-census-population-points `
  --output-csv data/population_points_tracts.csv `
  --raw-context-csv data/census_tract_context_2024.csv `
  --metadata-json data/census_tract_context_2024.metadata.json `
  --state NC `
  --year 2024
```

For all 51 jurisdictions, use `--state ALL` and review the larger output before routing:

```powershell
radshock fetch-census-population-points `
  --output-csv work/all-states/population_points_tracts.csv `
  --raw-context-csv work/all-states/census_tract_context_2024.csv `
  --metadata-json work/all-states/census_tract_context_2024.metadata.json `
  --state ALL `
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

Use `--state ALL` with separate output paths to prepare a 51-jurisdiction HRSA candidate-review sheet.
Those rows still require review and approval before they can be finalized:

```powershell
radshock prepare-hrsa-candidate-review `
  work/source-refresh-smoke/raw/hrsa-health-center-service-delivery-sites/2026-06-20/Health_Center_Service_Delivery_and_LookAlike_Sites.csv `
  --output-csv work/all-states/candidate_sites_review.csv `
  --metadata-json work/all-states/candidate_sites_review.metadata.json `
  --state ALL
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
