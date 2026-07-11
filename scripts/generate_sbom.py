from __future__ import annotations

import argparse
import json
import re
import tomllib
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REQ_NAME_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)")


def dependency_name(requirement: str) -> str:
    match = REQ_NAME_RE.match(requirement)
    if match is None:
        raise ValueError(f"Cannot parse dependency name from requirement: {requirement!r}")
    return match.group(1).replace("_", "-").lower()


def dependency_component(requirement: str, group: str, scope: str) -> dict[str, Any]:
    name = dependency_name(requirement)
    return {
        "type": "library",
        "bom-ref": f"pkg:pypi/{name}",
        "name": name,
        "scope": scope,
        "purl": f"pkg:pypi/{name}",
        "properties": [
            {"name": "radshock:requirement", "value": requirement},
            {"name": "radshock:dependency-group", "value": group},
        ],
    }


def build_sbom(pyproject: Path) -> dict[str, Any]:
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    project = data["project"]
    components: list[dict[str, Any]] = []

    for requirement in project.get("dependencies", []):
        components.append(dependency_component(requirement, "runtime", "required"))

    for group, requirements in sorted(project.get("optional-dependencies", {}).items()):
        for requirement in requirements:
            components.append(dependency_component(requirement, group, "optional"))

    components.sort(key=lambda component: (component["name"], component["scope"]))
    timestamp = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": timestamp,
            "tools": [
                {
                    "vendor": "radiology-access-shock-tracker",
                    "name": "scripts/generate_sbom.py",
                }
            ],
            "component": {
                "type": "application",
                "name": project["name"],
                "version": project["version"],
                "licenses": [{"license": {"id": project["license"]["text"]}}],
            },
            "properties": [
                {
                    "name": "radshock:sbom-scope",
                    "value": "direct dependencies from pyproject.toml",
                }
            ],
        },
        "components": components,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a direct-dependency CycloneDX SBOM from pyproject.toml."
    )
    parser.add_argument("--pyproject", type=Path, default=Path("pyproject.toml"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    sbom = build_sbom(args.pyproject)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(sbom, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
