# Radiology Access Shock Tracker

[![Tests](https://github.com/AKaturu/radiology-access-shock-tracker/actions/workflows/tests.yml/badge.svg)](https://github.com/AKaturu/radiology-access-shock-tracker/actions/workflows/tests.yml)

An open-source surveillance toolkit for detecting changes in mammography access, estimating which communities are affected, and comparing candidate response locations.

## Evidence Status

| Evidence | Status |
|---|---|
| Unit and integration tests | Complete (80 tests, ruff/mypy passing) |
| Synthetic end-to-end evaluation | Complete |
| Public-data evaluation | Partial (real NC FDA MQSA snapshot ingested, census data fetched, OSRM travel-time matrix generated for NC tracts) |
| Independent expert review | Not completed |
| Institutional validation | Not completed |
| Prospective clinical validation | Not completed |

This software is a research prototype and is not intended for independent clinical decision-making.

## Clinical Problem

Facility closures, relocations, and service reductions affect mammography access for specific communities. The FDA MQSA public file does not contain stable tracker IDs, coordinates, active status, or facility-level annual capacity. This project provides a rigorous, reproducible surveillance framework that keeps facility-change signals as verification prompts rather than definitive closure claims.

The `radshock demo` command creates **synthetic North Carolina-like data** and must not be interpreted as a real facility or utilization assessment. The public project uses synthetic data so it is easy to run and review. Reviewed real-data packages are documented separately.

## Dashboard Preview

![Dashboard overview](docs/assets/github/dashboard-overview.png)

Walkthrough footage and more screenshots are in [docs/GITHUB_PAGE_ASSETS.md](docs/GITHUB_PAGE_ASSETS.md).

## Capabilities

- Versions dated facility snapshots with SHA-256 checksums and metadata
- Detects new listings, possible closures, relocations, status changes, renames, and capacity reductions
- Calculates population-weighted distance or reviewed travel time to nearest active facility
- Produces vulnerability-adjusted county shock score and alert level
- Re-scores under alternative weighting assumptions for sensitivity review
- Audits analysis packages for publication-readiness blockers and provenance gaps
- Summarizes before/after screening utilization signals
- Ranks hypothetical mobile or fixed-site locations by geographic access recovery
- FDA MQSA source-refresh workflow with human-review gate
- Streamlit dashboard and Markdown policy brief exports

## Quick Start

```bash
pip install -e ".[dev]"
radshock demo --output-dir outputs/demo
streamlit run src/radshock/app.py
```

Then open the local Streamlit URL shown in the terminal.

## Use the Reviewed Real-Data Package

```bash
$env:RADSHOCK_ANALYSIS_DIR = "desktop_payload/analysis"
streamlit run src/radshock/app.py
```

The reviewed real NC no-observed-change validation package supports workflow and methods claims, but not trend, deterioration, or causal utilization claims.

## Limitations

- Facility disappearances are labeled `POSSIBLE_CLOSURE`, not confirmed closure
- Great-circle distance is the default demo method; travel-time matrices require reviewed routing
- Census ACS API queries require an API key
- Desktop artifacts are unsigned; public releases may trigger SmartScreen/Gatekeeper warnings
- Sensitivity scenarios test score robustness but do not clinically validate the score
- The initial scope is mammography access in North Carolina

## Documentation

| Topic | File |
|---|---|
| Methodology (formulas, thresholds, limitations) | [docs/METHODS.md](docs/METHODS.md) |
| Architecture | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Data sources (FDA, Census, CDC, HRSA, CMS) | [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) |
| Operations and credentials | [docs/OPERATIONS.md](docs/OPERATIONS.md) |
| Desktop releases | [docs/DESKTOP_RELEASES.md](docs/DESKTOP_RELEASES.md) |
| Roadmap | [docs/ROADMAP.md](docs/ROADMAP.md) |
| GitHub publishing | [docs/GITHUB_PUBLISHING.md](docs/GITHUB_PUBLISHING.md) |
| Journal report packaging | [docs/JOURNAL_REPORT_PACKAGE.md](docs/JOURNAL_REPORT_PACKAGE.md) |
| GitHub page assets | [docs/GITHUB_PAGE_ASSETS.md](docs/GITHUB_PAGE_ASSETS.md) |
| Contribution guide | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Security reporting | [SECURITY.md](SECURITY.md) |

## License

MIT. See [LICENSE](LICENSE). Public-source datasets remain governed by their respective source terms.
