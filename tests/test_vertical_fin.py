import math

import pytest

from carta_solar.config import DEVICE_VERTICAL_FIN, CartaSolarConfig
from carta_solar.devices.vertical_fin import (
    compute_vertical_fin_design,
    fin_depth_from_angle,
    horizontal_shadow_angle,
    is_protected_by_fin_angle,
)
from carta_solar.overhang import apply_computed_mask
from carta_solar.plot import generate_carta_solar


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
