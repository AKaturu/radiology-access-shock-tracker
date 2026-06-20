# Compiled Test Report

Generated from the local validation run on 2026-06-19 at 22:04 America/New_York.

## Result

Status: PASS

## Checks

- `python -m pytest --junitxml work/validation/pytest-junit.xml`: 66 passed in 7.37s.
- `python -m ruff check .`: passed.
- `python -m mypy src/radshock`: passed with no issues in 23 source files.
- `python -m pip wheel . -w work/dist`: built the project wheel.
- `radshock demo --output-dir work/validation/demo-smoke`: generated demo analysis, briefs, and
  readiness outputs.
- Streamlit health check at `http://127.0.0.1:8765/_stcore/health`: HTTP 200.

## Built Wheel

- File: `work/dist/radiology_access_shock_tracker-0.1.0-py3-none-any.whl`
- SHA-256: `2bf08a6e3b3ff3538b4f8d5caf7de86e7369358af5b67782fccc11031b05290a`

## Media Evidence

- Screenshots: `docs/assets/github/*.png`
- Walkthrough footage: `docs/assets/github/dashboard-walkthrough.webm`
- Capture script: `scripts/capture_github_assets.mjs`

## Boundary

The screenshots and walkthrough use synthetic demo data. They prove the application workflow and
publication-readiness gates render correctly; they are not real North Carolina findings.
