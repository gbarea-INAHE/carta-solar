import math

import numpy as np
import pytest

from carta_solar.config import DEVICE_VERTICAL_FIN, CartaSolarConfig
from carta_solar.devices.vertical_fin import (
    ShortFinDesign,
    compute_required_fin_angle,
    compute_vertical_fin_design,
    cut_angle_from_spacing,
    design_short_fins,
    design_short_fins_from_config,
    fin_count_for_width,
    fin_depth_from_angle,
    format_architect_fin_report,
    horizontal_shadow_angle,
    is_protected_by_fin_angle,
    min_beta_for_max_depth,
    recommended_fin_rotation,
    spacing_from_count,
    spacing_from_cut_angle,
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
    # W=2, β=45° → D = 1 / tan(45°) = 1 (ref. aleta profunda)
    assert fin_depth_from_angle(2.0, 45.0, bilateral=True) == pytest.approx(1.0)


def test_cut_angle_spacing_roundtrip():
    """tan(φ) = S/D."""
    depth = 0.50
    spacing = 0.30
    phi = cut_angle_from_spacing(depth, spacing)
    assert phi == pytest.approx(math.degrees(math.atan(spacing / depth)))
    assert spacing_from_cut_angle(depth, phi) == pytest.approx(spacing)


def test_fin_count_includes_jambs():
    # W=1.5, S_max=0.5 → ceil(1.5/0.5)+1 = 4
    assert fin_count_for_width(1.5, 0.5) == 4
    assert spacing_from_count(1.5, 4) == pytest.approx(0.5)


def test_lower_beta_protects_more():
    assert is_protected_by_fin_angle(120.0, 20.0, facade_az=90.0)
    assert not is_protected_by_fin_angle(100.0, 20.0, facade_az=90.0)


def test_east_facade_short_fin_design():
    config = CartaSolarConfig(
        lat=-34.0333,
        lon=-67.9167,
        facade_azimuth_override=90.0,
        device_mode=DEVICE_VERTICAL_FIN,
        critical_months=frozenset({11, 12, 1, 2}),
        critical_hour_start=7,
        critical_hour_end=12,
        window_width_m=1.5,
        fin_depth_m=0.50,
        use_civil_hours=False,
    )
    cut, depth, month = compute_vertical_fin_design(config)
    design = design_short_fins_from_config(config)
    assert depth == pytest.approx(0.50)
    assert design.n_fins >= 2
    assert design.spacing_m > 0
    assert design.spacing_m <= 1.5
    # Aletas cortas: D de obra, no la aleta profunda de ~2 m
    assert depth <= 1.20 + 1e-6
    if design.deep_fin_depth_m is not None:
        assert design.deep_fin_depth_m > depth
    assert 1.0 < cut < 90
    assert month is not None
    assert abs(design.rotation_deg) <= 45.0 + 1e-6


def test_short_fins_shallower_than_deep_single():
    """El paquete corto evita D≈2 m del modelo de una sola aleta."""
    design = design_short_fins(
        -34.0333,
        frozenset({11, 12, 1, 2}),
        7,
        12,
        window_width_m=1.5,
        depth_m=0.50,
        facade_az=90.0,
        lon=-67.9167,
        use_civil_hours=False,
    )
    assert design.depth_m == pytest.approx(0.50)
    assert design.n_fins >= 3
    assert design.deep_fin_depth_m is not None
    assert design.deep_fin_depth_m > design.depth_m * 2.0
    assert design.deep_fin_depth_m > 1.2


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
        fin_depth_m=0.45,
    )
    config = apply_computed_mask(base)
    assert config.mask_fin_angle is not None
    assert config.mask_alt is None
    assert config.fin_count is not None and config.fin_count >= 2
    assert config.fin_spacing_m is not None and config.fin_spacing_m > 0
    fig = generate_carta_solar(config)
    assert len(fig.axes) == 2
    assert "aletas" in fig.axes[1].get_title().lower() or "Planta" in fig.axes[1].get_title()


def test_fin_mask_rays_rotate_with_facade():
    """Rayo +φ en marco local debe caer en azimut facade±φ."""
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


def test_cut_angle_differs_by_facade_azimuth():
    """N / E / S no deben colapsar al mismo φ."""
    months = frozenset({11, 12, 1, 2, 3})
    common = dict(
        lat=-34.0333,
        lon=-67.9167,
        device_mode=DEVICE_VERTICAL_FIN,
        critical_months=months,
        window_width_m=1.5,
        fin_depth_m=0.50,
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
    cuts = {k: compute_vertical_fin_design(cfg)[0] for k, cfg in configs.items()}
    assert cuts["S"] > cuts["E"] + 5.0
    assert abs(cuts["N"] - cuts["E"]) > 2.0 or cuts["N"] > 15.0


def test_near_normal_sun_not_forcing_tiny_beta():
    """Con sol casi frontal, φ no debe caer a ~8° por mín |γ|."""
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
    assert result.beta_left_deg is not None or result.beta_right_deg is not None


def test_recommended_rotation_clamped_and_symmetric():
    assert recommended_fin_rotation([1.0, -1.0, 0.5, -0.5])[0] == pytest.approx(0.0)
    rot, _, _ = recommended_fin_rotation([40.0, 50.0, 60.0], max_abs_deg=45.0)
    assert rot == pytest.approx(45.0)
    rot_neg, _, _ = recommended_fin_rotation([-40.0, -50.0], max_abs_deg=45.0)
    assert rot_neg == pytest.approx(-45.0)


def test_architect_report_mentions_n_d_s_rotation():
    config = CartaSolarConfig(
        lat=-34.0333,
        lon=-67.9167,
        facade_azimuth_override=90.0,
        device_mode=DEVICE_VERTICAL_FIN,
        critical_months=frozenset({12, 1}),
        critical_hour_start=7,
        critical_hour_end=12,
        window_width_m=1.5,
        window_height_m=1.2,
        fin_depth_m=0.50,
        use_civil_hours=False,
    )
    design = design_short_fins_from_config(config)
    text = format_architect_fin_report(config, design)
    assert "Este" in text
    assert "1,50" in text or "1.50" in text
    assert f"{design.n_fins} parasoles" in text
    assert "proyección" in text
    assert "separados" in text
    assert "cm" in text
    assert "eje" in text or "perpendiculares" in text
    assert isinstance(design, ShortFinDesign)


def test_deeper_d_needs_fewer_fins():
    common = dict(
        lat=-34.0333,
        months=frozenset({12, 1}),
        hour_start=7,
        hour_end=12,
        window_width_m=1.5,
        facade_az=90.0,
        lon=-67.9167,
        use_civil_hours=False,
    )
    shallow = design_short_fins(**common, depth_m=0.30)
    deep = design_short_fins(**common, depth_m=0.80)
    assert deep.n_fins <= shallow.n_fins
    assert deep.spacing_m >= shallow.spacing_m
