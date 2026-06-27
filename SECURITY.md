# Security

## Reporting

Do not open public issues containing credentials, restricted datasets, patient information, or
unverified facility-status claims. Report sensitive concerns privately to the repository owner.

## Data Handling

This project is designed for public aggregate data and reviewed facility directories. It must not
store patient-level data or protected health information. API keys and source credentials belong in
local environment variables or untracked configuration files.

## Publication Boundary

Do not publish facility-change, access-loss, utilization, or intervention findings unless the
readiness audit is `READY` for the exact output package being shared. Synthetic demo packages and
unreviewed routing/candidate assumptions are intentionally blocked or warned by the audit.
