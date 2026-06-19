from pathlib import Path

import pandas as pd

from radshock.demo import build_demo


def test_demo_runs_end_to_end(tmp_path: Path) -> None:
    outputs = build_demo(tmp_path / "demo")
    assert all(path.exists() for path in outputs.values())
    events = pd.read_csv(outputs["events"])
    shocks = pd.read_csv(outputs["shocks"])
    interventions = pd.read_csv(outputs["interventions"])
    assert not events.empty
    assert not shocks.empty
    assert not interventions.empty
    assert "CLOSED" in set(events["event_type"])
