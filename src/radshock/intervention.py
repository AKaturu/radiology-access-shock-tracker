from __future__ import annotations

import numpy as np
import pandas as pd

from radshock.access import nearest_access
from radshock.geo import haversine_miles
from radshock.schemas import validate_candidates, validate_facilities


def simulate_candidates(
    population_points: pd.DataFrame,
    current_facilities: pd.DataFrame,
    candidates: pd.DataFrame,
    threshold_miles: float = 30.0,
) -> pd.DataFrame:
    """Rank hypothetical mobile or fixed sites using unconstrained geographic benefit."""
    candidate_rows = validate_candidates(candidates)
    current = nearest_access(population_points, validate_facilities(current_facilities))
    current_distance = current["distance_miles"].to_numpy(dtype=float)
    weights = current["weight"].to_numpy(dtype=float)
    rows: list[dict[str, object]] = []

    for candidate in candidate_rows.itertuples(index=False):
        candidate_distance = haversine_miles(
            current["latitude"].to_numpy(),
            current["longitude"].to_numpy(),
            float(candidate.latitude),
            float(candidate.longitude),
        )
        new_distance = np.minimum(current_distance, candidate_distance)
        reduction = np.maximum(0, current_distance - new_distance)
        recovered = (current_distance > threshold_miles) & (new_distance <= threshold_miles)
        improved = reduction > 0.1
        rows.append(
            {
                "candidate_id": candidate.candidate_id,
                "candidate_name": candidate.candidate_name,
                "county_fips": str(candidate.county_fips).zfill(5),
                "latitude": float(candidate.latitude),
                "longitude": float(candidate.longitude),
                "weighted_mean_distance_reduction": float(np.average(reduction, weights=weights)),
                "person_miles_reduced": float(np.sum(reduction * weights)),
                "population_brought_within_threshold": float(np.sum(weights[recovered])),
                "population_with_improved_access": float(np.sum(weights[improved])),
            }
        )

    result = pd.DataFrame(rows)
    if result.empty:
        return result
    person_max = max(float(result["person_miles_reduced"].max()), 1.0)
    recovered_max = max(float(result["population_brought_within_threshold"].max()), 1.0)
    result["intervention_score"] = 100 * (
        0.65 * result["person_miles_reduced"] / person_max
        + 0.35 * result["population_brought_within_threshold"] / recovered_max
    )
    result["intervention_score"] = result["intervention_score"].round(1)
    return result.sort_values(
        ["intervention_score", "candidate_name"], ascending=[False, True]
    ).reset_index(drop=True)
