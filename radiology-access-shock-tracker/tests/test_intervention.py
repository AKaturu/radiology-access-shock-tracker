import pandas as pd

from radshock.intervention import simulate_candidates


def test_closer_candidate_ranks_first() -> None:
    population = pd.DataFrame(
        [["P1", "37001", 35.0, -80.0, 1000]],
        columns=["point_id", "county_fips", "latitude", "longitude", "weight"],
    )
    facilities = pd.DataFrame(
        [["F1", "Far", 35.0, -78.0, 1000, True]],
        columns=[
            "facility_id",
            "facility_name",
            "latitude",
            "longitude",
            "annual_capacity",
            "active",
        ],
    )
    candidates = pd.DataFrame(
        [
            ["C1", "Near", "37001", 35.0, -80.0],
            ["C2", "Less Near", "37001", 35.0, -79.0],
        ],
        columns=["candidate_id", "candidate_name", "county_fips", "latitude", "longitude"],
    )
    result = simulate_candidates(population, facilities, candidates)
    assert result.loc[0, "candidate_name"] == "Near"
    assert result.loc[0, "intervention_score"] == 100.0
