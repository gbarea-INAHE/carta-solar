import pytest

from carta_solar.config import CartaSolarConfig


def test_default_config_is_valid():
    config = CartaSolarConfig.default()
    assert config.site_name == "Ñacuñán"
    assert config.mask_alt is None
    assert config.sill_height_m == 0.9
    assert config.window_height_m == 1.2
    assert config.gap_to_overhang_m == 0.3


def test_effective_shading_height():
    config = CartaSolarConfig(window_height_m=1.2, gap_to_overhang_m=0.3)
    assert config.effective_shading_height_m == pytest.approx(1.5)


def test_rejects_latitude_out_of_range():
    with pytest.raises(ValueError, match="latitud"):
        CartaSolarConfig(lat=95.0)


def test_mask_alt_none_disables_mask():
    config = CartaSolarConfig(mask_alt=None)
    assert config.mask_alt is None


def test_rejects_invalid_hour_range():
    with pytest.raises(ValueError, match="hora"):
        CartaSolarConfig(hour_start=20, hour_end=5)


def test_rejects_empty_critical_months():
    with pytest.raises(ValueError, match="mes"):
        CartaSolarConfig(critical_months=frozenset())


def test_rejects_non_positive_window_height():
    with pytest.raises(ValueError, match="ventana"):
        CartaSolarConfig(window_height_m=0)


def test_rejects_negative_sill_height():
    with pytest.raises(ValueError, match="antepecho"):
        CartaSolarConfig(sill_height_m=-0.1)


def test_rejects_negative_gap_to_overhang():
    with pytest.raises(ValueError, match="vano"):
        CartaSolarConfig(gap_to_overhang_m=-0.1)
