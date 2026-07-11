from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
PINNED_ACTION_RE = re.compile(r"uses:\s+[\w.-]+/[\w./-]+@[0-9a-f]{40}(?:\s+#\s*v\d+)?")
FLOATING_ACTION_RE = re.compile(r"uses:\s+[\w.-]+/[\w./-]+@v\d+")


def _load_generate_sbom() -> ModuleType:
    path = ROOT / "scripts" / "generate_sbom.py"
    spec = importlib.util.spec_from_file_location("generate_sbom", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_all_workflow_actions_are_pinned_to_full_commit_sha() -> None:
    workflow_paths = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
    assert workflow_paths

    for path in workflow_paths:
        text = path.read_text()
        assert not FLOATING_ACTION_RE.search(text), path
        for line in text.splitlines():
            if "uses:" in line and "docker://" not in line:
                assert PINNED_ACTION_RE.search(line), f"{path}: {line}"


def test_dependabot_tracks_python_and_github_actions() -> None:
    text = (ROOT / ".github" / "dependabot.yml").read_text()

    assert "package-ecosystem: pip" in text
    assert "package-ecosystem: github-actions" in text
    assert "open-pull-requests-limit" in text


def test_codeql_workflow_is_enabled_for_python() -> None:
    text = (ROOT / ".github" / "workflows" / "codeql.yml").read_text()

    assert "security-events: write" in text
    assert "languages: python" in text
    assert "github/codeql-action/init@" in text
    assert "github/codeql-action/analyze@" in text
    assert not FLOATING_ACTION_RE.search(text)


def test_desktop_release_publishes_checksums_and_sbom() -> None:
    text = (ROOT / ".github" / "workflows" / "desktop-release.yml").read_text()

    assert ".sha256" in text
    assert "radiology-access-shock-tracker-sbom.cdx.json" in text
    assert "scripts/generate_sbom.py" in text


def test_docker_context_excludes_local_data_and_review_artifacts() -> None:
    entries = set((ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines())

    assert {".git", ".venv", "data", "outputs", "tests", "work"} <= entries


def test_direct_dependency_sbom_contains_project_dependencies(tmp_path: Path) -> None:
    module = _load_generate_sbom()
    output = tmp_path / "sbom.cdx.json"

    sbom = module.build_sbom(ROOT / "pyproject.toml")
    output.write_text(json.dumps(sbom))

    payload = json.loads(output.read_text())
    component_names = {component["name"] for component in payload["components"]}

    assert payload["bomFormat"] == "CycloneDX"
    assert payload["metadata"]["component"]["name"] == "radiology-access-shock-tracker"
    assert "streamlit" in component_names
    assert "pyinstaller" in component_names
    assert payload["metadata"]["properties"][0]["value"] == (
        "direct dependencies from pyproject.toml"
    )
