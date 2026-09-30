import pytest

from carta_solar.solar import (
    alt_az_from_xy,
    profile_angle,
    r_from_alt,
    solar_alt_az,
    xy_from_alt_az,
)


def test_winter_solstice_noon_southern_hemisphere():
    alt, az = solar_alt_az(lat_deg=-34.0, day=172, hour_solar=12)
    assert alt > 0
    assert az == pytest.approx(0.0, abs=1.0)


def test_summer_solstice_noon_northern_hemisphere():
    alt, az = solar_alt_az(lat_deg=40.0, day=172, hour_solar=12)
    assert alt > 0
    assert az == pytest.approx(180.0, abs=1.0)


def test_stereographic_horizon_and_zenith():
    assert r_from_alt(0) == pytest.approx(1.0, rel=1e-6)
    assert r_from_alt(90) == pytest.approx(0.0, abs=1e-6)


def test_zenith_projection_is_origin():
    x, y = xy_from_alt_az(90, 0)
    assert x == pytest.approx(0.0, abs=1e-6)
    assert y == pytest.approx(0.0, abs=1e-6)


def test_profile_angle_at_facade_normal_equals_altitude():
    assert profile_angle(40.0, 0.0, facade_az=0.0) == pytest.approx(40.0, abs=1e-6)
    assert profile_angle(40.0, 180.0, facade_az=180.0) == pytest.approx(40.0, abs=1e-6)


def test_profile_angle_behind_facade_is_none():
    assert profile_angle(40.0, 180.0, facade_az=0.0) is None
    assert profile_angle(40.0, 0.0, facade_az=180.0) is None


def test_alt_az_xy_inverse():
    x, y = xy_from_alt_az(33.0, 215.0)
    alt, az = alt_az_from_xy(x, y)
    assert alt == pytest.approx(33.0, abs=1e-6)
    assert az == pytest.approx(215.0, abs=1e-6)
