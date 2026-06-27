import json
from pathlib import Path

import pandas as pd

from radshock.demo import build_demo


def test_demo_runs_end_to_end(tmp_path: Path) -> None:
    outputs = build_demo(tmp_path / "demo")
    assert all(path.exists() for path in outputs.values())
    events = pd.read_csv(outputs["events"])
    shocks = pd.read_csv(outputs["shocks"])
    interventions = pd.read_csv(outputs["interventions"])
    sensitivity = pd.read_csv(outputs["sensitivity"])
    readiness = json.loads(outputs["readiness_json"].read_text())
    assert not events.empty
    assert not shocks.empty
    assert not interventions.empty
    assert not sensitivity.empty
    assert "POSSIBLE_CLOSURE" in set(events["event_type"])
    assert outputs["brief_html"].exists()
    assert outputs["readiness_md"].exists()
    assert readiness["overall_status"] == "BLOCKED"
    assert "population_newly_over_30_miles" in shocks.columns
    assert "threshold_heavy" in set(sensitivity["scenario_id"])
