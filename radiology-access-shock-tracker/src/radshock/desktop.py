from __future__ import annotations

import argparse
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

APP_NAME = "Radiology Access Shock Tracker"


def main() -> None:
    args = _parse_args()
    if args.version:
        from radshock import __version__

        print(f"{APP_NAME} {__version__}")
        return

    analysis_dir = args.analysis_dir or _bundled_analysis_dir()
    if not analysis_dir.exists():
        raise SystemExit(
            f"Bundled analysis directory was not found: {analysis_dir}\n"
            "Set RADSHOCK_ANALYSIS_DIR or pass --analysis-dir to a reviewed analysis package."
        )
    _assert_required_outputs(analysis_dir)

    if args.check:
        print(f"Desktop payload OK: {analysis_dir}")
        return

    port = args.port or _find_free_port()
    url = f"http://127.0.0.1:{port}"
    os.environ["RADSHOCK_ANALYSIS_DIR"] = str(analysis_dir)
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")

    if not args.no_browser:
        threading.Thread(target=_open_browser_after_start, args=(url,), daemon=True).start()

    from streamlit.web import cli as streamlit_cli

    app_path = _streamlit_app_path()
    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.address",
        "127.0.0.1",
        "--server.port",
        str(port),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]
    streamlit_cli.main()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Launch the bundled Radiology Access Shock Tracker dashboard."
    )
    parser.add_argument("--analysis-dir", type=Path, help="Reviewed analysis package to open.")
    parser.add_argument("--port", type=int, help="Local dashboard port. Defaults to a free port.")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Start without opening a browser.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate the bundled payload and exit.",
    )
    parser.add_argument("--version", action="store_true", help="Print version and exit.")
    return parser.parse_args()


def _bundled_analysis_dir() -> Path:
    env_path = os.environ.get("RADSHOCK_ANALYSIS_DIR")
    if env_path:
        return Path(env_path)

    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    candidates = [
        bundle_root / "desktop_payload" / "analysis",
        Path.cwd() / "desktop_payload" / "analysis",
        Path(__file__).resolve().parents[2] / "desktop_payload" / "analysis",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _streamlit_app_path() -> Path:
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    candidates = [
        bundle_root / "radshock" / "app.py",
        Path(__file__).with_name("app.py"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise SystemExit("Bundled Streamlit app file was not found.")


def _assert_required_outputs(analysis_dir: Path) -> None:
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
            "Analysis package is missing required dashboard outputs: " + ", ".join(missing)
        )


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _open_browser_after_start(url: str) -> None:
    time.sleep(2.5)
    webbrowser.open(url)


if __name__ == "__main__":
    main()
