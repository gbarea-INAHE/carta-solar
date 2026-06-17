import math

import pytest

from carta_solar.config import CartaSolarConfig
from carta_solar.critical import compute_noon_alpha, DEFAULT_CRITICAL_MONTHS
from carta_solar.overhang import (
    apply_computed_mask,
    compute_overhang_from_config,
    overhang_projection,
)


def test_overhang_projection_formula():
    # H_eff=1.5 m, α=45° → P = 1.5 / tan(45°) = 1.5
    assert overhang_projection(1.5, 45) == pytest.approx(1.5, rel=1e-6)


def test_overhang_projection_uses_effective_height():
    h_eff = 1.2 + 0.3
    alpha = 55.0
    expected = h_eff / math.tan(math.radians(alpha))
    assert overhang_projection(h_eff, alpha) == pytest.approx(expected, rel=1e-6)


def test_noon_alpha_nacunan_sep_mar_range():
    alpha, month = compute_noon_alpha(-34.0333, frozenset({9, 10, 11, 12, 1, 2, 3}))
    assert 50 <= alpha <= 60
    assert month in {3, 9}


def test_overhang_depth_about_one_meter_for_user_case():
    config = CartaSolarConfig(
        lat=-34.0333,
        sill_height_m=1.5,
        window_height_m=1.0,
        gap_to_overhang_m=0.5,
        critical_months=frozenset({9, 10, 11, 12, 1, 2, 3}),
    )
    alpha, projection, _ = compute_overhang_from_config(config)
    assert 50 <= alpha <= 60
    assert 0.8 <= projection <= 1.3


def test_rejects_invalid_height():
    with pytest.raises(ValueError, match="altura"):
        overhang_projection(0, 55)


def test_compute_overhang_from_config_returns_alpha_and_projection():
    config = CartaSolarConfig(lat=-34.0333)
    alpha, projection, month = compute_overhang_from_config(config)
    assert 0 < alpha < 90
    assert month in DEFAULT_CRITICAL_MONTHS
    expected = config.effective_shading_height_m / math.tan(math.radians(alpha))
    assert projection == pytest.approx(expected, rel=1e-6)


def test_apply_computed_mask_sets_mask_alt():
    config = CartaSolarConfig(lat=-34.0333, mask_alt=None)
    updated = apply_computed_mask(config)
    assert updated.mask_alt is not None
    assert 50 <= updated.mask_alt <= 60
