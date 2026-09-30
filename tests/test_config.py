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


def test_facade_from_latitude():
    south = CartaSolarConfig(lat=-34.0)
    north = CartaSolarConfig.for_latitude(40.0)
    assert south.facade_azimuth == 0.0
    assert south.facade_label == "Norte"
    assert north.facade_azimuth == 180.0
    assert north.facade_label == "Sur"
    assert north.critical_months == frozenset({5, 6, 7, 8, 9})


def test_facade_azimuth_override():
    config = CartaSolarConfig(lat=-34.0, facade_azimuth_override=90.0)
    assert config.facade_azimuth == 90.0
    assert config.facade_label == "Este"


def test_site_name_truncated():
    long_name = "A" * 120
    config = CartaSolarConfig(site_name=long_name)
    assert len(config.site_name) == 80


def test_resolved_timezone_explicit_and_estimated():
    explicit = CartaSolarConfig(lon=-67.9167, timezone_utc_offset=-3.0)
    estimated = CartaSolarConfig(lon=-45.0, timezone_utc_offset=None)
    assert explicit.resolved_timezone_utc == -3.0
    assert estimated.resolved_timezone_utc == -3.0


def test_fin_depth_default_and_validation():
    cfg = CartaSolarConfig()
    assert cfg.fin_depth_m == pytest.approx(0.50)
    with pytest.raises(ValueError, match="profundidad"):
        CartaSolarConfig(fin_depth_m=0.0)
    with pytest.raises(ValueError, match="aletas"):
        CartaSolarConfig(fin_count=1)
