import matplotlib

matplotlib.use("Agg")

import pytest

from carta_solar.config import CartaSolarConfig
from carta_solar.critical import (
    DEFAULT_CRITICAL_MONTHS,
    collect_critical_samples,
    compute_required_alpha,
    find_unprotected_samples,
    is_in_front_of_facade,
)
from carta_solar.mask import facade_peak_xy, north_peak_y
from carta_solar.overhang import apply_computed_mask
from carta_solar.plot import generate_carta_solar


def test_front_sector_by_gamma_only():
    assert is_in_front_of_facade(90.0, facade_az=90.0)
    assert is_in_front_of_facade(0.0, facade_az=90.0)
    assert not is_in_front_of_facade(200.0, facade_az=90.0)


def test_nacunan_north_regression_solar_hours():
    alpha, samples, month = compute_required_alpha(
        -34.0333, DEFAULT_CRITICAL_MONTHS, 10, 18, facade_az=0.0
    )
    assert len(samples) == 65
    assert find_unprotected_samples(samples, alpha, facade_az=0.0) == []
    assert month in {3, 9}


def test_east_facade_has_morning_samples():
    samples = collect_critical_samples(
        -34.0333,
        frozenset({12, 1}),
        7,
        12,
        facade_az=90.0,
        use_civil_hours=False,
    )
    assert len(samples) > 0
    assert all(is_in_front_of_facade(s.az, 90.0) for s in samples)


def test_west_facade_has_afternoon_samples():
    samples = collect_critical_samples(
        -34.0333,
        frozenset({12, 1}),
        12,
        18,
        facade_az=270.0,
        use_civil_hours=False,
    )
    assert len(samples) > 0


def test_overhang_design_any_azimuth_plot():
    config = apply_computed_mask(
        CartaSolarConfig(
            lat=-34.0333,
            facade_azimuth_override=90.0,
            critical_months=frozenset({11, 12, 1}),
            critical_hour_start=8,
            critical_hour_end=14,
            use_civil_hours=False,
            chart_detail="preview",
        )
    )
    assert config.mask_alt is not None
    x, y = facade_peak_xy(config.mask_alt, facade_az=90.0)
    assert x == pytest.approx(north_peak_y(config.mask_alt), abs=1e-5)
    fig = generate_carta_solar(config)
    assert "Este" in fig.axes[1].get_title()
