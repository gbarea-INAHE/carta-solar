import matplotlib

matplotlib.use("Agg")

from matplotlib.lines import Line2D
from matplotlib.patches import PathPatch

from carta_solar.config import CartaSolarConfig
from carta_solar.mask import ACTIVE_LINE_COLOR, GRID_COLOR
from carta_solar.plot import build_output_basename, generate_carta_solar, save_carta_solar


def _shaded_patches(ax):
    return [
        p
        for p in ax.patches
        if isinstance(p, PathPatch) and p.get_alpha() is not None and p.get_alpha() > 0
    ]


def _colored_lines(ax, color):
    return [
        line
        for line in ax.get_lines()
        if isinstance(line, Line2D) and line.get_color() == color
    ]


def test_generate_carta_solar_returns_dual_panel_figure():
    config = CartaSolarConfig(mask_alt=55)
    figure = generate_carta_solar(config)
    assert figure is not None
    assert len(figure.axes) == 2


def test_section_panel_not_overlapping_solar_chart():
    config = CartaSolarConfig(mask_alt=55)
    figure = generate_carta_solar(config)
    ax_solar, ax_section = figure.axes

    assert ax_solar.get_title() == "Carta solar"
    assert ax_section.get_title() == "Sección — fachada Norte"
    assert ax_solar.bbox.x1 <= ax_section.bbox.x0


def test_protractor_draws_red_grid_and_gray_active_line():
    config = CartaSolarConfig(mask_alt=55)
    figure = generate_carta_solar(config)
    ax_solar = figure.axes[0]

    red_lines = _colored_lines(ax_solar, GRID_COLOR)
    gray_lines = _colored_lines(ax_solar, ACTIVE_LINE_COLOR)
    shaded = _shaded_patches(ax_solar)

    assert len(red_lines) >= 7
    assert len(gray_lines) >= 1
    assert len(shaded) >= 1


def test_no_protractor_when_disabled():
    config = CartaSolarConfig(mask_alt=None, highlight_critical_period=False)
    figure = generate_carta_solar(config)
    ax_solar = figure.axes[0]

    assert _colored_lines(ax_solar, GRID_COLOR) == []
    assert _colored_lines(ax_solar, ACTIVE_LINE_COLOR) == []
    assert _shaded_patches(ax_solar) == []


def test_section_placeholder_without_mask():
    config = CartaSolarConfig(mask_alt=None, highlight_critical_period=False)
    figure = generate_carta_solar(config)
    ax_section = figure.axes[1]
    texts = [t.get_text() for t in ax_section.texts]
    assert any("Calcular alero" in text for text in texts)


def test_hour_labels_rendered_above_overlays():
    config = CartaSolarConfig(mask_alt=55, hour_start=8, hour_end=14)
    figure = generate_carta_solar(config)
    ax_solar = figure.axes[0]
    hour_texts = [t for t in ax_solar.texts if t.get_text().isdigit()]
    assert hour_texts
    assert all(t.get_zorder() >= 10 for t in hour_texts)


def test_altitude_labels_have_no_background():
    config = CartaSolarConfig(mask_alt=55)
    figure = generate_carta_solar(config)
    ax_solar = figure.axes[0]
    alt_texts = [
        t
        for t in ax_solar.texts
        if t.get_text().endswith("°") and t.get_text()[:-1].isdigit()
    ]
    assert alt_texts
    assert all(t.get_bbox_patch() is None for t in alt_texts)
    assert all(t.get_zorder() >= 10 for t in alt_texts)


def test_hour_lines_use_distinct_style():
    config = CartaSolarConfig(mask_alt=55, hour_start=8, hour_end=12)
    figure = generate_carta_solar(config)
    ax_solar = figure.axes[0]
    hour_lines = [
        line
        for line in ax_solar.get_lines()
        if line.get_color() == "#1D6FBF"
    ]
    assert hour_lines
    assert all(line.get_linestyle() != "solid" for line in hour_lines)


def test_month_labels_use_chart_label_boxes():
    config = CartaSolarConfig(mask_alt=55)
    figure = generate_carta_solar(config)
    ax_solar = figure.axes[0]
    month_texts = [t for t in ax_solar.texts if t.get_text().startswith("21 ")]
    assert month_texts
    assert all(t.get_bbox_patch() is not None for t in month_texts)
    assert all(t.get_fontsize() >= 9 for t in month_texts)


def test_build_output_basename_with_and_without_mask():
    with_mask = CartaSolarConfig(site_name="Ñacuñán", mask_alt=55)
    without_mask = CartaSolarConfig(site_name="Ñacuñán", mask_alt=None)

    assert build_output_basename(with_mask) == "carta_solar_nacunan_mascara_55"
    assert build_output_basename(without_mask) == "carta_solar_nacunan"


def test_save_carta_solar_writes_files(tmp_path):
    config = CartaSolarConfig(site_name="Test", output_dir=tmp_path, mask_alt=45)
    figure = generate_carta_solar(config)

    saved = save_carta_solar(figure, config, png=True, pdf=True)

    assert saved["png"].exists()
    assert saved["pdf"].exists()
    assert saved["png"].name == "carta_solar_test_mascara_45.png"
