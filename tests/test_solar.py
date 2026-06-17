import pytest

from carta_solar.solar import r_from_alt, solar_alt_az, xy_from_alt_az


def test_winter_solstice_noon_southern_hemisphere():
    alt, az = solar_alt_az(lat_deg=-34.0, day=172, hour_solar=12)
    assert alt > 0
    assert az == pytest.approx(0.0, abs=1.0)


def test_stereographic_horizon_and_zenith():
    assert r_from_alt(0) == pytest.approx(1.0, rel=1e-6)
    assert r_from_alt(90) == pytest.approx(0.0, abs=1e-6)


def test_zenith_projection_is_origin():
    x, y = xy_from_alt_az(90, 0)
    assert x == pytest.approx(0.0, abs=1e-6)
    assert y == pytest.approx(0.0, abs=1e-6)
