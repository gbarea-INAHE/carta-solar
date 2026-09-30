import matplotlib

matplotlib.use("Agg")

import pytest

from carta_solar.annotations import draw_section_diagram
from carta_solar.config import CartaSolarConfig
from carta_solar.overhang import apply_computed_mask


@pytest.fixture
def section_axes():
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(4, 5))
    yield ax
    plt.close(fig)


def test_draw_section_diagram_with_computed_mask(section_axes):
    config = apply_computed_mask(CartaSolarConfig(lat=-34.0333))
    draw_section_diagram(section_axes, config)

    labels = [t.get_text() for t in section_axes.texts]
    assert any("h_s" in text for text in labels)
    assert any("h_v" in text for text in labels)
    assert any("h_g" in text for text in labels)
    assert any("P =" in text for text in labels)
    assert any("α =" in text for text in labels)


def test_draw_vertical_fin_plan_short_fins(section_axes):
    config = apply_computed_mask(
        CartaSolarConfig(
            lat=-34.0333,
            facade_azimuth_override=90.0,
            device_mode="vertical_fin",
            critical_months=frozenset({12, 1}),
            critical_hour_start=8,
            critical_hour_end=12,
            window_width_m=1.5,
            fin_depth_m=0.50,
            use_civil_hours=False,
        )
    )
    draw_section_diagram(section_axes, config)
    labels = [t.get_text() for t in section_axes.texts]
    joined = " ".join(labels)
    assert "D =" in joined
    assert "S =" in joined or "cm" in joined
    assert any("N =" in text for text in labels)
    assert "aletas" in section_axes.get_title().lower()


def test_draw_section_diagram_placeholder_without_mask(section_axes):
    config = CartaSolarConfig(mask_alt=None)
    draw_section_diagram(section_axes, config)

    texts = [t.get_text() for t in section_axes.texts]
    assert any("Calcular alero" in text for text in texts)
