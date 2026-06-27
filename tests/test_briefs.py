import pandas as pd

from radshock.briefs import generate_policy_brief


def test_policy_brief_describes_travel_time_shocks_in_minutes() -> None:
    brief = generate_policy_brief(
        events=pd.DataFrame(columns=["event_type"]),
        county_shocks=pd.DataFrame(
            [
                {
                    "county_name": "Demo",
                    "alert_level": "WARNING",
                    "shock_score": 12.3,
                    "access_metric": "travel_time_minutes",
                    "mean_travel_time_delta": 4.5,
                    "p90_travel_time_delta": 6.7,
                }
            ]
        ),
        interventions=pd.DataFrame(),
    )

    assert "mean travel-time change +4.5 minutes" in brief
    assert "routing backend" in brief
