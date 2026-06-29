import numpy as np
import pandas as pd
import pytest

from radshock.geo import haversine_miles


def test_identical_points_zero_distance() -> None:
    lat, lon = 35.7796, -78.6382
    result = haversine_miles(lat, lon, lat, lon)
    assert result.shape == ()
    assert float(result) == 0.0


def test_known_distance_nyc_to_la() -> None:
    nyc_lat, nyc_lon = 40.7128, -74.0060
    la_lat, la_lon = 34.0522, -118.2437
    result = haversine_miles(nyc_lat, nyc_lon, la_lat, la_lon)
    assert float(result) == pytest.approx(2445, abs=20)


def test_scalar_input_returns_float_array() -> None:
    result = haversine_miles(35.0, -78.0, 36.0, -79.0)
    assert isinstance(result, np.ndarray)
    assert result.ndim == 0
    assert float(result) > 0


def test_series_input_returns_array() -> None:
    lats = pd.Series([35.0, 36.0, 34.0])
    lons = pd.Series([-78.0, -79.0, -80.0])
    result = haversine_miles(lats, lons, lats + 0.5, lons - 0.5)
    assert isinstance(result, np.ndarray)
    assert result.shape == (3,)
    assert all(result > 0)
