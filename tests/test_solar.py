import pytest

from carta_solar.solar import (
    alt_az_from_xy,
    civil_to_solar_hour,
    estimate_timezone_utc,
    equation_of_time_minutes,
    profile_angle,
    r_from_alt,
    solar_alt_az,
    solar_alt_az_at_clock,
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


def test_estimate_timezone_from_longitude():
    # Estimación geográfica (el huso político se elige en la UI; AR = UTC−3).
    assert estimate_timezone_utc(-67.9167) == -5.0
    assert estimate_timezone_utc(-45.0) == -3.0
    assert estimate_timezone_utc(0.0) == 0.0


def test_civil_to_solar_west_of_standard_meridian():
    # lon=-60, tz=-3 → lon_std=-45 → −1 h + EoT
    day = 172
    eot_h = equation_of_time_minutes(day) / 60.0
    solar = civil_to_solar_hour(12.0, -60.0, day, timezone_utc_hours=-3.0)
    assert solar == pytest.approx(12.0 - 1.0 + eot_h, abs=1e-6)


def test_solar_alt_az_at_clock_civil_differs_from_solar():
    lat, lon, day = -34.0, -67.9167, 80
    alt_s, az_s = solar_alt_az_at_clock(lat, lon, day, 12.0, use_civil_hours=False)
    alt_c, az_c = solar_alt_az_at_clock(
        lat, lon, day, 12.0, use_civil_hours=True, timezone_utc_hours=-3.0
    )
    assert alt_s != pytest.approx(alt_c, abs=0.5)
    # Con horas solares, mediodía ≈ az Norte
    assert az_s == pytest.approx(0.0, abs=2.0)
