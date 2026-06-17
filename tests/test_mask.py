import numpy as np
import pytest

from carta_solar.mask import (
    alpha_curve_points,
    build_shaded_region_vertices,
    circle_params_for_alpha,
    north_peak_y,
)
from carta_solar.solar import r_from_alt


def test_north_peak_matches_stereographic_radius():
    for alpha in (10, 30, 55, 80):
        assert north_peak_y(float(alpha)) == pytest.approx(r_from_alt(alpha), rel=1e-6)


def test_alpha_curves_equidistant_on_north_meridian():
    """Cada arco α corta el eje N en r(α): equidistante en grados como la grilla."""
    y10 = north_peak_y(10.0)
    y20 = north_peak_y(20.0)
    y30 = north_peak_y(30.0)
    assert y10 == pytest.approx(r_from_alt(10), rel=1e-6)
    assert y20 == pytest.approx(r_from_alt(20), rel=1e-6)
    assert y30 == pytest.approx(r_from_alt(30), rel=1e-6)
    assert y10 > y20 > y30


def test_alpha_curve_passes_through_west_north_east():
    points = alpha_curve_points(55.0, num_points=181)
    north = (0.0, r_from_alt(55.0))

    assert points[0] == pytest.approx(WEST := (-1.0, 0.0), abs=1e-6)
    assert points[-1] == pytest.approx((1.0, 0.0), abs=1e-6)

    peak_idx = np.argmax(points[:, 1])
    assert points[peak_idx, 0] == pytest.approx(0.0, abs=0.02)
    assert points[peak_idx, 1] == pytest.approx(north[1], abs=0.02)


def test_alpha_curve_is_a_circular_arc():
    """Todos los puntos del arco equidistan del centro de la circunferencia."""
    y_c, radius, _ = circle_params_for_alpha(55.0)
    points = alpha_curve_points(55.0, num_points=60)
    center = np.array([0.0, y_c])
    distances = np.linalg.norm(points - center, axis=1)
    assert np.all(distances == pytest.approx(radius, rel=1e-6, abs=1e-6))


def test_shaded_region_in_northern_semicircle():
    vertices = build_shaded_region_vertices(55.0)
    assert np.all(vertices[:, 1] >= -1e-9)


def test_shaded_region_has_positive_area():
    vertices = build_shaded_region_vertices(55.0)
    x = vertices[:, 0]
    y = vertices[:, 1]
    area = 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
    assert area > 0.1
