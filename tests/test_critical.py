import numpy as np
import pytest

from carta_solar.critical import (
    DEFAULT_CRITICAL_MONTHS,
    DEFAULT_CRITICAL_MONTHS_HN,
    collect_critical_samples,
    compute_noon_alpha,
    compute_required_alpha,
    find_unprotected_samples,
    format_exposure_report,
    is_point_shaded_by_alpha,
    is_protected_by_alpha,
    max_y_on_alpha_arc,
    min_alpha_for_point,
    required_alpha_for_point,
)
from carta_solar.mask import alpha_curve_points, north_peak_y
from carta_solar.solar import alt_az_from_xy, profile_angle, xy_from_alt_az


def test_alt_az_from_xy_roundtrip():
    x, y = xy_from_alt_az(45.0, 30.0)
    alt, az = alt_az_from_xy(x, y)
    assert alt == pytest.approx(45.0, abs=1e-6)
    assert az == pytest.approx(30.0, abs=1e-6)


def test_solar_ar_arcs_are_iso_profile():
    """Los arcos SOL-AR coinciden con curvas iso-perfil ε = α (fachada Norte)."""
    for alpha in (20.0, 40.0, 56.37, 70.0):
        for x, y in alpha_curve_points(alpha, num_points=40):
            if abs(y) < 1e-9:
                continue
            alt, az = alt_az_from_xy(float(x), float(y))
            eps = profile_angle(alt, az, facade_az=0.0)
            assert eps is not None
            assert eps == pytest.approx(alpha, abs=1e-6)


def test_north_peak_requires_matching_alpha():
    x, y = 0.0, north_peak_y(55.0)
    assert min_alpha_for_point(x, y) == pytest.approx(55.0, abs=1e-6)


def test_point_at_horizon_east_behind_or_edge():
    x, y = xy_from_alt_az(0.0, 90.0)
    # Sol en el Este al horizonte: cos γ ≈ 0 → detrás/borde → ε None → 0.0
    assert min_alpha_for_point(x, y) == pytest.approx(0.0, abs=1e-9)


def test_required_alpha_for_noon_north():
    eps = required_alpha_for_point(56.37, 0.0, facade_az=0.0)
    assert eps == pytest.approx(56.37, abs=1e-6)


def test_is_protected_high_sun_yes_low_sun_no():
    alpha = 56.37
    assert is_protected_by_alpha(70.0, 0.0, alpha, facade_az=0.0)
    assert not is_protected_by_alpha(20.0, 0.0, alpha, facade_az=0.0)


def test_is_point_shaded_matches_protection():
    alpha = 56.37
    x70, y70 = xy_from_alt_az(70.0, 0.0)
    x20, y20 = xy_from_alt_az(20.0, 0.0)
    assert is_point_shaded_by_alpha(x70, y70, alpha)
    assert not is_point_shaded_by_alpha(x20, y20, alpha)


def test_lower_alpha_protects_more():
    """α menor protege más (alero más profundo)."""
    x = 0.0
    # Punto con ε ≈ 45° (pico del arco 45°)
    y = max_y_on_alpha_arc(x, 45.0)
    assert is_point_shaded_by_alpha(x, y, 45.0)
    assert is_point_shaded_by_alpha(x, y, 30.0)
    assert not is_point_shaded_by_alpha(x, y, 60.0)


def test_arc_edge_is_protected():
    alpha = 56.37
    x, y = 0.0, north_peak_y(alpha)
    assert is_point_shaded_by_alpha(x, y, alpha)


def test_nacunan_summer_full_coverage():
    lat = -34.0333
    months = DEFAULT_CRITICAL_MONTHS
    alpha, samples, month = compute_required_alpha(lat, months, 10, 18)
    assert len(samples) == 65
    assert month in {3, 9}
    unprotected = find_unprotected_samples(samples, alpha, facade_az=0.0)
    assert unprotected == []
    report = format_exposure_report(
        samples, alpha, limiting_month=month, facade_az=0.0
    )
    assert "65/65" in report
    assert "completamente cubierto" in report


def test_required_alpha_close_to_noon_in_summer():
    lat = -34.0333
    noon, noon_month = compute_noon_alpha(lat, DEFAULT_CRITICAL_MONTHS)
    required, _, req_month = compute_required_alpha(
        lat, DEFAULT_CRITICAL_MONTHS, 10, 18
    )
    assert required == pytest.approx(noon, abs=0.05)
    assert req_month == noon_month


def test_winter_required_alpha_below_noon():
    lat = -34.0333
    winter = frozenset({5, 6, 7})
    noon, _ = compute_noon_alpha(lat, winter)
    required, samples, _ = compute_required_alpha(lat, winter, 10, 18)
    assert samples
    assert required < noon


def test_northern_hemisphere_summer_coverage():
    lat = 40.0
    months = DEFAULT_CRITICAL_MONTHS_HN
    alpha, samples, month = compute_required_alpha(
        lat, months, 10, 18, facade_az=180.0
    )
    assert len(samples) > 0
    assert 0 < alpha < 90
    assert month is not None
    unprotected = find_unprotected_samples(samples, alpha, facade_az=180.0)
    assert unprotected == []


def test_compute_required_alpha_no_samples_returns_90():
    # Latitud alta + meses de invierno polar → sin muestras
    alpha, samples, month = compute_required_alpha(
        80.0, frozenset({12}), 10, 18, facade_az=180.0
    )
    assert alpha == 90.0
    assert samples == []
    assert month is None
