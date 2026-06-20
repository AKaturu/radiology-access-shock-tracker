# Desktop Downloads

The project can build portable desktop dashboard downloads for Windows, macOS, and Linux with the
`desktop release` GitHub Actions workflow.

## What Users Download

The workflow produces:

- `RadiologyAccessShockTracker-windows-x64.zip`
- `RadiologyAccessShockTracker-macos-x64.dmg`
- `RadiologyAccessShockTracker-linux-x64.tar.gz`

These are unsigned builds. Windows SmartScreen and macOS Gatekeeper may warn on first launch until
the project has code-signing certificates and notarization.

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

1. Push the repository to GitHub.
2. Open **Actions**.
3. Select **desktop release**.
4. Click **Run workflow**.
5. Download the uploaded artifacts from the completed workflow run.

The workflow also runs automatically for tags that start with `v`.

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
