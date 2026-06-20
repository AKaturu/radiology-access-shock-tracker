# GitHub Page Assets

These assets are ready for a README, GitHub Pages page, or release notes. The current checked-in
screenshots and walkthrough were captured from the reviewed real North Carolina self-hosted OSRM
analysis package at `work/self-hosted-osrm/analysis-tract-self-hosted-osrm`, not from the synthetic
demo. The package readiness audit was `READY` with 0 blockers and 0 warnings.

The current real-data boundary still matters: the reviewed `2026-06-19` to `2026-06-20` comparison
is a no-observed-change validation run, not evidence of a longitudinal access trend.

## Primary Preview

```markdown
![Dashboard overview](docs/assets/github/dashboard-overview.png)
```

![Dashboard overview](assets/github/dashboard-overview.png)

## Walkthrough Footage

Use this as linked test footage:

```markdown
[Watch dashboard walkthrough](docs/assets/github/dashboard-walkthrough.webm)
```

[Watch dashboard walkthrough](assets/github/dashboard-walkthrough.webm)

## Screenshot Set

- [Overview dashboard](assets/github/dashboard-overview.png)
- [County shocks table](assets/github/county-shocks.png)
- [Intervention ranking](assets/github/interventions.png)
- [Sensitivity review](assets/github/sensitivity.png)
- [Readiness audit](assets/github/readiness-audit.png)
- [Mobile overview](assets/github/mobile-overview.png)

## Regenerate

After regenerating or restoring the reviewed real analysis package, start the app with that package
as the dashboard source, then run the capture script:

```powershell
$env:RADSHOCK_ANALYSIS_DIR = "work/self-hosted-osrm/analysis-tract-self-hosted-osrm"
streamlit run src/radshock/app.py --server.port 8765

$env:RADSHOCK_CAPTURE_URL = "http://127.0.0.1:8765"
node scripts/capture_github_assets.mjs
```

The script uses `RADSHOCK_CAPTURE_URL`, `RADSHOCK_CAPTURE_OUTPUT`, and
`RADSHOCK_CHROMIUM_EXECUTABLE` if you need a different app URL, destination directory, or browser.
It fails by default if the loaded dashboard shows the synthetic-data warning. For intentional demo
captures only, set `RADSHOCK_CAPTURE_ALLOW_SYNTHETIC=1`.
