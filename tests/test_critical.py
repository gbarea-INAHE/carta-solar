import numpy as np
import pytest

from carta_solar.critical import (
    DEFAULT_CRITICAL_MONTHS,
    collect_critical_samples,
    compute_minimum_alpha,
    compute_noon_alpha,
    find_unprotected_samples,
    is_point_shaded_by_alpha,
    max_y_on_alpha_arc,
    min_alpha_for_point,
)
from carta_solar.mask import north_peak_y
from carta_solar.solar import xy_from_alt_az


def test_north_peak_requires_at_least_55_alpha():
    x, y = 0.0, north_peak_y(55.0)
    assert min_alpha_for_point(x, y) == pytest.approx(55.0, abs=2.0)


def test_point_at_horizon_east_needs_low_alpha():
    x, y = xy_from_alt_az(0.0, 90.0)
    assert min_alpha_for_point(x, y) <= 5.0


def test_compute_minimum_alpha_nacunan_summer():
    alpha_min, samples = compute_minimum_alpha(
        lat=-34.0333,
        months=DEFAULT_CRITICAL_MONTHS,
        hour_start=10,
        hour_end=18,
    )
    assert len(samples) > 0
    assert 10 <= alpha_min <= 89


def test_compute_noon_alpha_nacunan():
    alpha, month = compute_noon_alpha(-34.0333, DEFAULT_CRITICAL_MONTHS)
    assert 50 <= alpha <= 60
    assert month in {3, 9}


def test_higher_alpha_shades_more():
    x = 0.0
    y = max_y_on_alpha_arc(x, 45.0) + 0.05
    assert is_point_shaded_by_alpha(x, y, 45.0)
    assert not is_point_shaded_by_alpha(x, y, 30.0)


def test_find_unprotected_with_high_alpha():
    samples = collect_critical_samples(-34.0333, DEFAULT_CRITICAL_MONTHS, 10, 18)
    unprotected = find_unprotected_samples(samples, 10.0)
    assert len(unprotected) <= len(samples)
