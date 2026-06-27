# Contributing

## Development Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy src/radshock
```

Use equivalent `python` and activation commands on macOS or Linux.

## Quality Gates

Run before opening or updating a pull request:

```powershell
python -m ruff check .
python -m mypy src/radshock
python -m pytest
```

For user-facing dashboard or demo changes, also run:

```powershell
radshock demo --output-dir outputs/demo
streamlit run src/radshock/app.py
```

## Data Rules

- Do not commit credentials, tokens, restricted downloads, caches, or large generated outputs.
- Keep synthetic data clearly labeled.
- Do not describe disappeared facilities as confirmed closures without independent verification.
- Add fixture-based or mocked tests for adapter changes.
- Update methods and limitations when analytic behavior changes.
