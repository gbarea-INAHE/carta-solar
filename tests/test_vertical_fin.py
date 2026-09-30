import math

import numpy as np
import pytest

from carta_solar.config import DEVICE_VERTICAL_FIN, CartaSolarConfig
from carta_solar.devices.vertical_fin import (
    compute_required_fin_angle,
    compute_vertical_fin_design,
    fin_depth_from_angle,
    horizontal_shadow_angle,
    is_protected_by_fin_angle,
    min_beta_for_max_depth,
    suggested_critical_hours,
)
from carta_solar.mask import rotate_points
from carta_solar.overhang import apply_computed_mask
from carta_solar.plot import generate_carta_solar
from carta_solar.solar import alt_az_from_xy


def test_horizontal_shadow_angle_on_normal():
    assert horizontal_shadow_angle(90.0, facade_az=90.0) == pytest.approx(0.0)


def test_horizontal_shadow_angle_behind_is_none():
    assert horizontal_shadow_angle(270.0, facade_az=90.0) is None


def test_fin_depth_bilateral_formula():
    # W=2, β=45° → D = 1 / tan(45°) = 1
    assert fin_depth_from_angle(2.0, 45.0, bilateral=True) == pytest.approx(1.0)


def test_lower_beta_protects_more():
    assert is_protected_by_fin_angle(120.0, 20.0, facade_az=90.0)
    assert not is_protected_by_fin_angle(100.0, 20.0, facade_az=90.0)


def test_east_facade_vertical_design():
    config = CartaSolarConfig(
        lat=-34.0333,
        lon=-67.9167,
        facade_azimuth_override=90.0,
        device_mode=DEVICE_VERTICAL_FIN,
        critical_months=frozenset({11, 12, 1, 2}),
        critical_hour_start=7,
        critical_hour_end=12,
        window_width_m=1.5,
        use_civil_hours=False,
    )
    beta, depth, month = compute_vertical_fin_design(config)
    assert 8 <= beta < 90
    assert depth > 0
    assert depth <= 2.5 + 1e-6  # tope constructivo por defecto
    assert month is not None


def test_apply_vertical_mask_and_plot():
    import matplotlib

    matplotlib.use("Agg")
    base = CartaSolarConfig(
        lat=-34.0333,
        facade_azimuth_override=90.0,
        device_mode=DEVICE_VERTICAL_FIN,
        critical_months=frozenset({12, 1}),
        critical_hour_start=8,
        critical_hour_end=12,
        use_civil_hours=False,
        chart_detail="preview",
    )
    config = apply_computed_mask(base)
    assert config.mask_fin_angle is not None
    assert config.mask_alt is None
    fig = generate_carta_solar(config)
    assert len(fig.axes) == 2
    assert "aletas" in fig.axes[1].get_title().lower() or "Planta" in fig.axes[1].get_title()


def test_fin_mask_rays_rotate_with_facade():
    """Rayo +β en marco local debe caer en azimut facade±β."""
    beta = 30.0
    for facade_az in (0.0, 90.0, 180.0, 270.0, 45.0):
        local = np.array(
            [[np.sin(np.radians(beta)), np.cos(np.radians(beta))]]
        )
        pts = rotate_points(local, facade_az)[0]
        _alt, az = alt_az_from_xy(float(pts[0]), float(pts[1]))
        expected = (facade_az + beta) % 360.0
        diff = abs(((az - expected) + 180) % 360 - 180)
        assert diff < 1.0, f"facade={facade_az}: az={az} expected={expected}"


def test_beta_design_differs_by_facade_azimuth():
    """N / E / S no deben colapsar al mismo β≈9° (bug del mín |γ|)."""
    months = frozenset({11, 12, 1, 2, 3})
    common = dict(
        lat=-34.0333,
        lon=-67.9167,
        device_mode=DEVICE_VERTICAL_FIN,
        critical_months=months,
        window_width_m=1.5,
        use_civil_hours=False,
    )
    configs = {
        "N": CartaSolarConfig(
            **common,
            facade_azimuth_override=0.0,
            critical_hour_start=10,
            critical_hour_end=18,
        ),
        "E": CartaSolarConfig(
            **common,
            facade_azimuth_override=90.0,
            critical_hour_start=7,
            critical_hour_end=12,
        ),
        "S": CartaSolarConfig(
            **common,
            facade_azimuth_override=180.0,
            critical_hour_start=10,
            critical_hour_end=18,
        ),
    }
    betas = {k: compute_vertical_fin_design(cfg)[0] for k, cfg in configs.items()}
    # Sur (invierno solar en HS) debe ser claramente más alto que Este
    assert betas["S"] > betas["E"] + 10.0
    # Norte y Este no deben ser casi idénticos por el piso de 8°
    assert abs(betas["N"] - betas["E"]) > 2.0 or betas["N"] > 15.0


def test_near_normal_sun_not_forcing_tiny_beta():
    """Con sol casi frontal, β no debe caer a ~8° por mín |γ|."""
    result = compute_required_fin_angle(
        -34.0333,
        frozenset({12, 1}),
        10,
        14,
        facade_az=0.0,
        use_civil_hours=False,
        percentile=25.0,
        near_normal_deg=15.0,
        min_beta_deg=None,
    )
    assert result.n_near_normal > 0
    # Sin tope de profundidad, el percentil sobre φ usable debe superar el viejo piso
    assert result.beta_deg > 10.0


def test_min_beta_caps_max_depth():
    beta_min = min_beta_for_max_depth(1.5, 2.5, bilateral=True)
    depth = fin_depth_from_angle(1.5, beta_min, bilateral=True)
    assert depth == pytest.approx(2.5, rel=1e-6)


def test_suggested_critical_hours_follow_facade_preset():
    assert suggested_critical_hours(90.0) == (7, 12)
    assert suggested_critical_hours(270.0) == (12, 18)
    assert suggested_critical_hours(0.0) == (10, 18)
    assert suggested_critical_hours(100.0) == (7, 12)


def test_asymmetric_beta_left_right_reported():
    result = compute_required_fin_angle(
        -34.0333,
        frozenset({12, 1}),
        7,
        12,
        facade_az=90.0,
        use_civil_hours=False,
    )
    assert result.n_frontal > 0
    # En Este por la mañana suele haber γ de un signo dominante
    assert result.beta_left_deg is not None or result.beta_right_deg is not None
