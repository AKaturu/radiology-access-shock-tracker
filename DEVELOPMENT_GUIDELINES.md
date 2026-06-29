# Development Guidelines

## Mission

Maintain a rigorous, reproducible public-health surveillance project that detects changes in mammography access and estimates community impact. Do not describe a facility as definitively closed or a utilization change as caused by a facility event without verified evidence.

## Engineering Rules

- Keep synthetic demo data clearly labeled.
- Preserve snapshot immutability and provenance metadata.
- Require explicit schemas and fail loudly on missing columns.
- Add tests for every scoring, matching, or geographic-method change.
- Keep source adapters separate from core analysis.
- Surface measurement year, source date, and uncertainty in user-facing outputs.
- Do not silently impute missing facility IDs or coordinates.
- Avoid patient-level or protected health information.

## Scope

The initial scope is mammography access-shock tracking in North Carolina. New diagnostic-resolution, multimodality, workforce-vulnerability, or advanced equity-optimization modules should be proposed through normal roadmap discussion and reviewed before implementation.

## Definition Of Done

- `pytest` passes.
- `ruff check .` passes.
- New public functions have type hints and docstrings.
- Methods and limitations are updated when analytic behavior changes.
- Demo pipeline still runs from a clean checkout.
