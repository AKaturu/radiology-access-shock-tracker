# PROJECT_STATE

## Project Overview

### Project Name
Radiology Access Shock Tracker

### Goal
Add 50-state source access to the radiology access workflow while preserving the reviewed North
Carolina validation package and keeping the public GitHub Pages documentation accurate.

### Current Status
Validation complete on branch `codex/github-page-fixes`.

---

## Completed Features

### Feature: 50-State Source Access

#### Validation
- `python -m pytest -q`: passed, 89 tests.
- `ruff check .`: passed.
- `mypy src/radshock`: passed with no issues in 26 source files.
- Rendered local Markdown link audit: passed for 12 Markdown files.

#### Tests Added
- `tests/test_adapters.py`: state-scope parsing, CDC PLACES all-state filtering, ACS national
  Gazetteer/ACS joining, HRSA all-state filtering.
- `tests/test_cli.py`: `prepare-mqsa-review --state ALL` coverage and updated metadata assertions.

---

## Current Work

### Active Feature
None.

### Progress
All requested implementation, docs, and validation updates are complete locally.

### Remaining Work
Push the branch and open a PR if remote publication is desired.

---

## Next Actions

1. Review the local commit on `codex/github-page-fixes`.
2. Push the branch to GitHub when ready.
3. Run real 50-state source workflows with production credentials and human review before
   publishing non-NC findings.

---

## Risks

### Open Questions
None for the local implementation.

### Known Issues
- GitHub shows one open pull request, #5 "Build production readiness reporting"; no open issue was
  found for the Pages repo.

### Technical Concerns
- `--state ALL` prepares 50-state inputs, but it does not remove the existing human-review,
  geocoding, route-matrix, and readiness gates required before publishing real findings.

---

## Resume Instructions

Start with `src/radshock/states.py`, `src/radshock/adapters/acs.py`, and `src/radshock/cli.py`.
Verify with `python -m pytest -q`, `ruff check .`, and `mypy src/radshock`. The single next step is
to push `codex/github-page-fixes` and open a PR if the GitHub repo should receive these changes.
