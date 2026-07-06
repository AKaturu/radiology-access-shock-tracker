from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

APP_NAME = "RadiologyAccessShockTracker"


def main() -> None:
    args = _parse_args()
    project_root = Path(__file__).resolve().parents[1]
    payload_dir = project_root / "desktop_payload"
    launcher = project_root / "scripts" / "desktop_launcher.py"
    app_file = project_root / "src" / "radshock" / "app.py"
    _assert_payload(payload_dir / "analysis")

    dist_dir = args.dist_dir or (project_root / "dist" / "desktop")
    work_dir = args.work_dir or (project_root / "build" / "desktop")
    separator = ";" if os.name == "nt" else ":"
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--name",
        APP_NAME,
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(work_dir),
        "--specpath",
        str(work_dir),
        "--add-data",
        f"{payload_dir}{separator}desktop_payload",
        "--add-data",
        f"{app_file}{separator}radshock",
        "--collect-all",
        "streamlit",
        "--collect-all",
        "plotly",
    ]
    if args.windowed:
        command.append("--windowed")
    command.append(str(launcher))
    subprocess.run(command, cwd=project_root, check=True)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the desktop dashboard bundle.")
    parser.add_argument("--dist-dir", type=Path)
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--windowed", action="store_true")
    return parser.parse_args()


def _assert_payload(analysis_dir: Path) -> None:
    required = [
        "county_shocks.csv",
        "facility_events.csv",
        "intervention_rankings.csv",
        "manifest.json",
        "policy_brief.md",
        "readiness_audit.json",
        "readiness_audit.md",
        "sensitivity_analysis.csv",
    ]
    missing = [name for name in required if not (analysis_dir / name).exists()]
    if missing:
        raise SystemExit(
            "Desktop payload is missing required analysis files: " + ", ".join(missing)
        )


if __name__ == "__main__":
    main()
