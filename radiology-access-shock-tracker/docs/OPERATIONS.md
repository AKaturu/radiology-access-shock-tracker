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

## External Credentials

Do not commit production credentials. Configure them as GitHub repository or organization secrets
when workflows start using those integrations.

Expected external credentials:

- `CENSUS_API_KEY`: required for ACS API pulls in environments where the Census API rejects keyless requests.
- Routing provider credentials: required only after an approved road-time provider is selected and wired into a workflow.

The current quarterly FDA review-artifact workflow does not use these secrets.

## Census API Key

The Census Bureau states that all Census Data API queries now require an API key. Request a key at:

<https://api.census.gov/data/key_signup.html>

After the key is issued and activated, store it locally as `CENSUS_API_KEY` or configure it as a
GitHub repository/organization secret with the same name. Do not commit the key.

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

Before finalization, reviewers must record or verify:

- provider and endpoint
- road network vintage or map data date
- travel mode/profile
- traffic assumption, if any
- unreachable/excluded route policy
- license/attribution requirements

Only after that review should `review_status` be changed from `needs_review` to `reviewed`,
`verified`, or `approved`, followed by `radshock finalize-travel-time-review`.
