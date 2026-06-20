# GitHub Page Assets

These assets are ready for a README, GitHub Pages page, or release notes. They use synthetic demo
outputs only.

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

Start the app, then run the capture script:

```bash
radshock demo --output-dir outputs/demo
streamlit run src/radshock/app.py --server.port 8765
node scripts/capture_github_assets.mjs
```

The script uses `RADSHOCK_CAPTURE_URL` and `RADSHOCK_CAPTURE_OUTPUT` if you need a different app
URL or destination directory.
