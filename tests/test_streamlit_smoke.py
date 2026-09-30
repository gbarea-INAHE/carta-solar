import matplotlib

matplotlib.use("Agg")

from dataclasses import replace

from streamlit_app import (
    AppState,
    build_config_from_state,
    figure_to_png_bytes,
    should_recalculate,
    _default_state,
)
from carta_solar.overhang import apply_computed_mask
from carta_solar.plot import generate_carta_solar


def test_build_config_from_state_defaults():
    state = _default_state()
    config = build_config_from_state(state)
    assert config.site_name == "Ñacuñán"
    assert config.lat == -34.0333
    assert config.mask_alt is None


def test_build_config_from_state_custom():
    state = AppState(
        site_name="Test",
        lat=-30.0,
        lon=-60.0,
        sill_height_m=1.0,
        window_height_m=1.1,
        gap_to_overhang_m=0.4,
        critical_months=frozenset({3, 9}),
        critical_hour_start=8,
        critical_hour_end=17,
        hour_start=6,
        hour_end=18,
        highlight_critical_period=False,
    )
    config = build_config_from_state(state)
    assert config.window_height_m == 1.1
    assert config.critical_months == frozenset({3, 9})


def test_build_config_from_state_web_figsize():
    state = _default_state()
    config = build_config_from_state(state, for_web=True)
    assert config.figsize == (12.0, 6.0)
    assert config.dpi == 120


def test_generate_figure_from_state_pipeline():
    config = apply_computed_mask(build_config_from_state(_default_state()))
    fig = generate_carta_solar(config)
    assert fig is not None
    assert len(fig.axes) == 2
    png = figure_to_png_bytes(fig)
    assert len(png) > 1000


def test_generate_figure_northern_hemisphere():
    from carta_solar.critical import DEFAULT_CRITICAL_MONTHS_HN

    state = AppState(
        site_name="Madrid",
        lat=40.4,
        lon=-3.7,
        sill_height_m=0.9,
        window_height_m=1.2,
        gap_to_overhang_m=0.3,
        critical_months=DEFAULT_CRITICAL_MONTHS_HN,
        critical_hour_start=10,
        critical_hour_end=18,
        hour_start=5,
        hour_end=19,
        highlight_critical_period=True,
    )
    config = apply_computed_mask(build_config_from_state(state))
    assert config.facade_label == "Sur"
    assert 0 < config.mask_alt < 90
    fig = generate_carta_solar(config)
    assert len(fig.axes) == 2


def test_should_recalculate_on_first_render():
    state = _default_state()
    assert should_recalculate(state, None, has_figure=False) is True


def test_should_recalculate_when_inputs_change():
    state = _default_state()
    changed = replace(state, lat=-30.0)
    assert should_recalculate(changed, state, has_figure=True) is True
    assert should_recalculate(state, state, has_figure=True) is False


def test_should_recalculate_on_force_button():
    state = _default_state()
    assert should_recalculate(state, state, force=True, has_figure=True) is True
