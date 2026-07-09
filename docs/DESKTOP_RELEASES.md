# Desktop Downloads

The project builds portable desktop dashboard downloads for Windows, macOS, and Linux with the
`desktop release` GitHub Actions workflow. Tag pushes such as `v0.2.0` publish the artifacts to a
GitHub Release.

## What Users Download

The workflow produces:

- `RadiologyAccessShockTracker-windows-x64.zip`
- `RadiologyAccessShockTracker-macos-x64.dmg`
- `RadiologyAccessShockTracker-linux-x64.tar.gz`
- `.sha256` checksum files for each downloadable artifact
- `radiology-access-shock-tracker-sbom.cdx.json`

The Windows ZIP contains `RadiologyAccessShockTracker.exe`. These are unsigned builds. Windows
SmartScreen and macOS Gatekeeper may warn on first launch until the project has code-signing
certificates and notarization.

## What Is Bundled

The desktop app bundles the reviewed real North Carolina analysis package in
`desktop_payload/analysis`.

Current bundled evidence:

- Reviewed MQSA snapshots: `2026-06-19` and `2026-06-20`
- Facility rows: 289 active records in each snapshot
- Route package: self-hosted OSRM driving profile
- Route rows: 52,680 of 52,680 routed
- Readiness audit: `READY`, 0 blockers, 0 warnings
- Finding boundary: no observed facility events and no warning/critical county shocks in this
  no-change validation run

## API Keys

Users do **not** need API keys to open the bundled dashboard.

API keys are only needed for data-refresh work:

- `CENSUS_API_KEY`: required for new Census Data API queries. The Census developer site says all
  Census Data API queries now require a key.
- `OPENROUTESERVICE_API_KEY`: only needed if using hosted OpenRouteService routing drafts. The
  publishable route-time path uses self-hosted OSRM instead, so no ORS key is needed for the bundled
  dashboard or the self-hosted OSRM workflow.

References:

- Census API developer page: <https://www.census.gov/data/developers/data-sets.html>
- OpenRouteService API docs: <https://openrouteservice.org/dev/>
- PyInstaller platform note: <https://www.pyinstaller.org/>

## Build Downloads On GitHub

1. Push a tag such as `v0.2.0`, or open **Actions** and select **desktop release**.
2. The workflow builds Windows, Linux, and macOS artifacts on their native runners.
   macOS x64 builds use GitHub's `macos-15-intel` runner label.
3. The workflow writes SHA-256 checksum files and a direct-dependency CycloneDX SBOM.
4. For tag pushes, the workflow publishes the artifacts to the matching GitHub Release.
5. For manual runs, download the uploaded artifacts from the completed workflow run. Set
   `publish_release` and `release_tag` when you want the manual run to publish a release.

The workflow also runs automatically for tags that start with `v`.

## Release Trust Record

For each public desktop release, open a release-trust issue with
`.github/ISSUE_TEMPLATE/release_trust.yml`. Record:

- release URL and version
- checksum files for Windows, macOS, and Linux artifacts
- SBOM upload
- downloaded-artifact checksum verification
- Windows code-signing status
- macOS code-signing and notarization status

Code signing and notarization are not automated yet because they require signing certificates,
secure secret storage, and Apple Developer notarization credentials. Until those are configured,
the release-trust issue should explicitly mark the binaries as unsigned.

## Local Build

Install the project with desktop build dependencies:

```bash
python -m pip install -e ".[desktop]"
python -m radshock.desktop --check
```

Build a local bundle for the current OS:

```bash
python scripts/build_desktop.py
```

For Windows or macOS GUI-style builds:

```bash
python scripts/build_desktop.py --windowed
```

PyInstaller is not a cross-compiler, so Windows, macOS, and Linux artifacts must be built on their
respective operating systems. The GitHub Actions workflow does that for you.
