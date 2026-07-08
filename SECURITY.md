# Security

## Reporting

Do not open public issues containing credentials, restricted datasets, patient information, or
unverified facility-status claims. Report sensitive concerns privately to the repository owner.

## Data Handling

This project is designed for public aggregate data and reviewed facility directories. It must not
store patient-level data or protected health information. API keys and source credentials belong in
local environment variables or untracked configuration files.

## Supply Chain

The repository uses Dependabot for Python and GitHub Actions updates, CodeQL for static analysis,
full-length commit SHA pins for reusable GitHub Actions, and release checksum/SBOM artifacts for
future desktop releases. Release checksums and SBOMs support verification and dependency review;
they do not replace platform code signing or macOS notarization.
