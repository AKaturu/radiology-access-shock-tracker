# GitHub Page Assets

These assets are ready for a README, GitHub Pages page, or release notes. The current checked-in
screenshots and walkthrough are intentionally captured from the synthetic demo, not the reviewed
real North Carolina package. That keeps the public GitHub demo easy to run, easy to understand, and
clearly separated from publishable real-data claims.

The warning banner in the screenshots is expected. It proves the dashboard visibly blocks synthetic
outputs from being mistaken for real North Carolina findings.

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

Regenerate the synthetic demo, start the app with the demo analysis package, then run the capture
script with synthetic capture explicitly allowed:

```powershell
python -m radshock.cli demo --output-dir outputs/demo
$env:RADSHOCK_ANALYSIS_DIR = "outputs/demo/analysis"
streamlit run src/radshock/app.py --server.port 8765

$env:RADSHOCK_CAPTURE_URL = "http://127.0.0.1:8765"
$env:RADSHOCK_CAPTURE_ALLOW_SYNTHETIC = "1"
node scripts/capture_github_assets.mjs
```

The script uses `RADSHOCK_CAPTURE_URL`, `RADSHOCK_CAPTURE_OUTPUT`, and
`RADSHOCK_CHROMIUM_EXECUTABLE` if you need a different app URL, destination directory, or browser.
It fails by default if the loaded dashboard shows the synthetic-data warning; the
`RADSHOCK_CAPTURE_ALLOW_SYNTHETIC=1` flag is required for these intentional public demo captures.

For reviewed real-data screenshots, set `RADSHOCK_ANALYSIS_DIR` to a reviewed analysis package such
as `desktop_payload/analysis` and leave `RADSHOCK_CAPTURE_ALLOW_SYNTHETIC` unset.
