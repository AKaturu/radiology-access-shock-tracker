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
