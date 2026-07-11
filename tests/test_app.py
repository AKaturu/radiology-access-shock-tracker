from pathlib import Path

from streamlit.testing.v1 import AppTest

from radshock.demo import build_demo

APP_PATH = Path(__file__).parents[1] / "src" / "radshock" / "app.py"


def test_dashboard_renders_generated_demo(monkeypatch, tmp_path: Path) -> None:
    outputs = build_demo(tmp_path / "demo")
    analysis_dir = outputs["events"].parent
    monkeypatch.setenv("RADSHOCK_ANALYSIS_DIR", str(analysis_dir))

    app = AppTest.from_file(str(APP_PATH), default_timeout=20).run()

    assert not app.exception
    assert app.title[0].value == "Radiology Access Shock Tracker"
    assert [tab.label for tab in app.tabs] == [
        "Overview",
        "Facility events",
        "County shocks",
        "Interventions",
        "Utilization",
        "Sensitivity",
        "Readiness",
        "Methods",
    ]
    metric_labels = {item.label for item in app.metric}
    assert {"Facility events", "Counties flagged", "Highest shock score"} <= metric_labels
    assert any("Synthetic demonstration data" in item.value for item in app.warning)


def test_dashboard_explains_missing_analysis(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("RADSHOCK_ANALYSIS_DIR", str(tmp_path / "missing"))

    app = AppTest.from_file(str(APP_PATH), default_timeout=10).run()

    assert not app.exception
    assert any("Run `radshock demo` first" in item.value for item in app.warning)
