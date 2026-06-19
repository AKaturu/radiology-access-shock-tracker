from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray

EARTH_RADIUS_MILES = 3958.7613


def haversine_miles(
    lat1: ArrayLike,
    lon1: ArrayLike,
    lat2: ArrayLike,
    lon2: ArrayLike,
) -> NDArray[np.float64]:
    """Vectorized great-circle distance in miles."""
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2)
    lon2_rad = np.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2
    result = 2 * EARTH_RADIUS_MILES * np.arcsin(np.sqrt(a))
    return np.asarray(result, dtype=np.float64)
