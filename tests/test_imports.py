"""Smoke de imports usados por Streamlit (evita regresiones en Cloud)."""

from __future__ import annotations


def test_config_exports_without_numpy_side_effects():
    import sys

    # Quitar critical/solar si ya estaban (el test debe poder cargar config solo).
    for name in list(sys.modules):
        if name.startswith("carta_solar"):
            del sys.modules[name]

    from carta_solar.config import (
        DEVICE_OVERHANG,
        DEVICE_VERTICAL_FIN,
        SITE_NAME_MAX_LEN,
        CartaSolarConfig,
    )

    assert DEVICE_OVERHANG == "overhang"
    assert DEVICE_VERTICAL_FIN == "vertical_fin"
    assert SITE_NAME_MAX_LEN == 80
    assert CartaSolarConfig.default().site_name == "Ñacuñán"
    # config liviano: no debe haber forzado plot todavía
    assert "carta_solar.plot" not in sys.modules


def test_package_getattr_lazy():
    import carta_solar

    assert carta_solar.__version__
    cls = carta_solar.CartaSolarConfig
    assert cls is not None


def test_streamlit_app_import_chain():
    """Misma cadena que streamlit_app.py tras el bootstrap."""
    from carta_solar.branding import AUTHORS, CREDIT_LINE, INSTITUTION, available_logos
    from carta_solar.config import (
        DEVICE_OVERHANG,
        DEVICE_VERTICAL_FIN,
        SITE_NAME_MAX_LEN,
        CartaSolarConfig,
    )
    from carta_solar.critical import (
        DEFAULT_CRITICAL_MONTHS,
        MONTH_NAMES,
        collect_critical_samples,
        compute_required_alpha,
        default_critical_months_for_lat,
        facade_azimuth_for_lat,
        facade_label_for_azimuth,
        format_exposure_report,
    )
    from carta_solar.devices.vertical_fin import (
        compute_vertical_fin_design,
        find_unprotected_by_fin,
    )
    from carta_solar.overhang import apply_computed_mask, overhang_projection
    from carta_solar.plot import build_output_basename, generate_carta_solar
    from carta_solar.solar import estimate_timezone_utc

    assert AUTHORS
    assert CREDIT_LINE
    assert INSTITUTION
    assert callable(available_logos)
    assert DEVICE_OVERHANG and DEVICE_VERTICAL_FIN and SITE_NAME_MAX_LEN
    assert CartaSolarConfig is not None
    assert DEFAULT_CRITICAL_MONTHS and MONTH_NAMES
    assert callable(collect_critical_samples)
    assert callable(compute_required_alpha)
    assert callable(default_critical_months_for_lat)
    assert callable(facade_azimuth_for_lat)
    assert callable(facade_label_for_azimuth)
    assert callable(format_exposure_report)
    assert callable(compute_vertical_fin_design)
    assert callable(find_unprotected_by_fin)
    assert callable(apply_computed_mask)
    assert callable(overhang_projection)
    assert callable(build_output_basename)
    assert callable(generate_carta_solar)
    assert callable(estimate_timezone_utc)
