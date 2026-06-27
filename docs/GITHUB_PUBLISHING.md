# GitHub Publishing Guide

This guide packages the repository for GitHub without publishing ignored local build artifacts such
as `.venv/`, `work/`, OSRM graph files, caches, or raw private working directories.

## Current Publishability Status

Local production-readiness checks pass for the self-hosted OSRM package:

- Readiness audit: `READY`, 0 blockers, 0 warnings.
- Route matrix: 52,680 of 52,680 tract-nearest facility pairs routed.
- Routing provider: self-hosted Project OSRM via Docker, `osrm:driving`.
- Map extract: Geofabrik North Carolina, OSM timestamp `2026-06-19T20:21:41Z`.
- Real MQSA snapshots: reviewed `2026-06-19` and `2026-06-20` NC facility snapshots.
- Current finding boundary: no observed change between those two snapshots. Do not make trend,
  deterioration, or causal claims until a future FDA MQSA source update is reviewed.

## What To Publish

Use the source ZIP built under `dist/github/` or create a fresh archive with:

```powershell
git archive --format zip `
  --prefix radiology-access-shock-tracker/ `
  --output radiology-access-shock-tracker-source.zip `
  HEAD:radiology-access-shock-tracker
```

That archive contains tracked source, docs, tests, reviewed public-data inputs, synthetic demo
screenshots, and workflow templates. It intentionally excludes ignored local directories.

## Create The GitHub Repository

Recommended clean flow:

1. Create an empty GitHub repository named `radiology-access-shock-tracker`.
2. Unzip the source archive into a new folder.
3. In that unzipped folder, initialize and push:

```powershell
cd path\to\radiology-access-shock-tracker
git init
git add .
git commit -m "Initial public release"
git branch -M main
git remote add origin https://github.com/<OWNER>/radiology-access-shock-tracker.git
git push -u origin main
```

If you use GitHub CLI instead:

```powershell
cd path\to\radiology-access-shock-tracker
git init
git add .
git commit -m "Initial public release"
git branch -M main
gh repo create <OWNER>/radiology-access-shock-tracker --public --source . --remote origin --push
```

After pushing, confirm the README test badge points at the published repository owner.

Official GitHub references:

- Adding locally hosted code to GitHub:
  <https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github>
- Quickstart for repositories:
  <https://docs.github.com/en/repositories/creating-and-managing-repositories/quickstart-for-repositories>

## Enable GitHub Pages

This repository includes `docs/index.md`, synthetic demo screenshots, and validation notes suitable
for a project page.

1. Go to the GitHub repository.
2. Open **Settings** > **Pages**.
3. Set source to **Deploy from a branch**.
4. Select branch `main` and folder `/docs`.
5. Save.

Official GitHub Pages publishing-source reference:
<https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site>

## Configure Governance

Before relying on scheduled refreshes or external contributions:

1. Install and authenticate GitHub CLI.
2. Set optional live-source secrets in the local shell:

```powershell
$env:GITHUB_REPOSITORY = "<OWNER>/radiology-access-shock-tracker"
$env:CENSUS_API_KEY = "<your-census-key>"
$env:OPENROUTESERVICE_API_KEY = "<your-openrouteservice-key>"
```

3. Dry-run the governance setup:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\configure_github_governance.ps1
```

4. Apply it after reviewing the planned changes:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\configure_github_governance.ps1 -Apply
```

The script sets repository secrets from environment variables and applies
`.github/branch-protection.main.json` by default. The protection template requires one code-owner
review, the `test` status check, resolved conversations, stale-review dismissal, and blocks force
pushes and branch deletion.

Official GitHub branch-protection reference:
<https://docs.github.com/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches>

## Manual Workflows To Run After Publication

- **tests**: runs automatically on pushes and pull requests.
- **desktop release**: manually dispatch to build Windows, macOS, and Linux desktop dashboard
  downloads from the bundled reviewed analysis package.
- **quarterly MQSA source refresh**: manually dispatch once to verify artifact generation in
  GitHub Actions, then leave the quarterly schedule enabled.
- **self-hosted OSRM travel-time package**: run manually when you want a CI-hosted artifact for
  the production route-time package.

## Public Claim Checklist

Before writing a public-facing GitHub release or project page:

- Label the README and Pages screenshots as synthetic demo media.
- Keep real-data findings separate from the public demo.
- For real-data release notes, confirm the latest readiness audit is `READY`.
- For real-data release notes, state that the current real comparison is `2026-06-19` versus
  `2026-06-20`.
- For real-data release notes, state that no facility events or warning/critical county shocks were
  observed in that comparison.
- Do not claim longitudinal deterioration until a future FDA MQSA source update is reviewed.
- Do not claim facility-level annual capacity, because FDA MQSA public data do not publish it.
- Label HRSA candidate response sites as planning assumptions, not mammography-capable sites.
