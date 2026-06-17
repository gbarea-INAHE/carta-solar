"""Versión web de Carta Solar — Aleros Norte (Streamlit)."""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import streamlit as st

from carta_solar.branding import AUTHORS, CREDIT_LINE, INSTITUTION, available_logos
from carta_solar.config import CartaSolarConfig
from carta_solar.critical import (
    DEFAULT_CRITICAL_MONTHS,
    MONTH_NAMES,
    collect_critical_samples,
    compute_noon_alpha,
    format_exposure_report,
)
from carta_solar.overhang import apply_computed_mask, overhang_projection
from carta_solar.plot import build_output_basename, generate_carta_solar

# Tamaño base de la figura; en pantalla se muestra al ~50% del ancho principal.
WEB_FIGSIZE = (12.0, 6.0)
WEB_DISPLAY_DPI = 120
EXPORT_DPI = 300
CHART_WIDTH_RATIO = 0.75


@dataclass(frozen=True)
class AppState:
    site_name: str
    lat: float
    lon: float
    sill_height_m: float
    window_height_m: float
    gap_to_overhang_m: float
    critical_months: frozenset[int]
    critical_hour_start: int
    critical_hour_end: int
    hour_start: int
    hour_end: int
    highlight_critical_period: bool


def build_config_from_state(
    state: AppState,
    *,
    for_web: bool = False,
) -> CartaSolarConfig:
    """Construye configuración sin calcular α (para tests y formulario)."""
    web_kwargs = (
        {"figsize": WEB_FIGSIZE, "dpi": WEB_DISPLAY_DPI} if for_web else {}
    )
    return CartaSolarConfig(
        site_name=state.site_name,
        lat=state.lat,
        lon=state.lon,
        hour_start=state.hour_start,
        hour_end=state.hour_end,
        output_dir=Path("salida"),
        sill_height_m=state.sill_height_m,
        window_height_m=state.window_height_m,
        gap_to_overhang_m=state.gap_to_overhang_m,
        critical_months=state.critical_months,
        critical_hour_start=state.critical_hour_start,
        critical_hour_end=state.critical_hour_end,
        highlight_critical_period=state.highlight_critical_period,
        **web_kwargs,
    )


def figure_to_png_bytes(fig: plt.Figure, *, dpi: int = 300) -> bytes:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=dpi, bbox_inches="tight")
    buffer.seek(0)
    return buffer.getvalue()


def _default_state() -> AppState:
    return AppState(
        site_name="Ñacuñán",
        lat=-34.0333,
        lon=-67.9167,
        sill_height_m=0.9,
        window_height_m=1.2,
        gap_to_overhang_m=0.3,
        critical_months=DEFAULT_CRITICAL_MONTHS,
        critical_hour_start=10,
        critical_hour_end=18,
        hour_start=5,
        hour_end=19,
        highlight_critical_period=True,
    )


def _sidebar_state() -> AppState:
    st.sidebar.header("Ubicación")
    site_name = st.sidebar.text_input("Nombre del sitio", value="Ñacuñán")
    lat = st.sidebar.number_input("Latitud (Sur = −)", value=-34.0333, format="%.4f")
    lon = st.sidebar.number_input("Longitud (Oeste = −)", value=-67.9167, format="%.4f")

    st.sidebar.header("Medidas en corte (m)")
    sill_height_m = st.sidebar.number_input("Antepecho (piso → ventana)", value=0.9, min_value=0.0, step=0.05)
    window_height_m = st.sidebar.number_input("Altura ventana", value=1.2, min_value=0.01, step=0.05)
    gap_to_overhang_m = st.sidebar.number_input("Vano (cierre ventana → alero)", value=0.3, min_value=0.0, step=0.05)

    st.sidebar.header("Período crítico")
    month_options = st.sidebar.multiselect(
        "Meses críticos",
        options=list(range(1, 13)),
        default=sorted(DEFAULT_CRITICAL_MONTHS),
        format_func=lambda m: MONTH_NAMES[m],
    )
    selected_months = set(month_options)
    crit_h1, crit_h2 = st.sidebar.columns(2)
    with crit_h1:
        critical_hour_start = st.number_input("Hora crítica inicio", value=10, min_value=0, max_value=23, step=1)
    with crit_h2:
        critical_hour_end = st.number_input("Hora crítica fin", value=18, min_value=1, max_value=23, step=1)
    highlight_critical_period = st.sidebar.checkbox("Resaltar período crítico en carta", value=True)

    st.sidebar.header("Carta")
    h1, h2 = st.sidebar.columns(2)
    with h1:
        hour_start = st.number_input("Hora inicio (líneas)", value=5, min_value=0, max_value=23, step=1)
    with h2:
        hour_end = st.number_input("Hora fin (líneas)", value=19, min_value=1, max_value=23, step=1)

    if not selected_months:
        selected_months = set(DEFAULT_CRITICAL_MONTHS)

    return AppState(
        site_name=site_name.strip() or "Sitio",
        lat=float(lat),
        lon=float(lon),
        sill_height_m=float(sill_height_m),
        window_height_m=float(window_height_m),
        gap_to_overhang_m=float(gap_to_overhang_m),
        critical_months=frozenset(selected_months),
        critical_hour_start=int(critical_hour_start),
        critical_hour_end=int(critical_hour_end),
        hour_start=int(hour_start),
        hour_end=int(hour_end),
        highlight_critical_period=highlight_critical_period,
    )


def main() -> None:
    st.set_page_config(page_title="Carta Solar — Aleros Norte", layout="wide")
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] {
            width: 17rem !important;
            min-width: 17rem !important;
        }
        section[data-testid="stSidebar"] > div {
            width: 17rem !important;
            min-width: 17rem !important;
        }
        .block-container {
            padding-top: 1rem;
            max-width: none;
        }
        [data-testid="stMetricValue"] { font-size: 1.35rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("Carta Solar — Aleros Norte")
    st.caption(f"{AUTHORS}  |  {INSTITUTION}")

    logos = available_logos()
    if logos:
        cols = st.columns(len(logos))
        for col, logo_path in zip(cols, logos, strict=False):
            col.image(str(logo_path), width=120)

    state = _sidebar_state()
    calc = st.sidebar.button("Calcular alero", type="primary", use_container_width=True)

    if calc or "figure" not in st.session_state:
        try:
            base_config = build_config_from_state(state, for_web=True)
            config = apply_computed_mask(base_config)
            fig = generate_carta_solar(config)
            depth = overhang_projection(config.effective_shading_height_m, config.mask_alt)
            samples = collect_critical_samples(
                config.lat,
                config.critical_months,
                config.critical_hour_start,
                config.critical_hour_end,
            )
            _, noon_month = compute_noon_alpha(config.lat, config.critical_months)
            report = format_exposure_report(samples, config.mask_alt, noon_month=noon_month)
            st.session_state["figure"] = fig
            st.session_state["config"] = config
            st.session_state["depth"] = depth
            st.session_state["report"] = report
        except ValueError as exc:
            st.error(str(exc))
            return
        except Exception as exc:
            st.error(f"No se pudo calcular el alero: {exc}")
            return

    if "figure" not in st.session_state:
        st.info("Completá los parámetros en la barra lateral y pulsá **Calcular alero**.")
        return

    config: CartaSolarConfig = st.session_state["config"]
    fig: plt.Figure = st.session_state["figure"]
    depth: float = st.session_state["depth"]
    report: str = st.session_state["report"]

    m1, m2, m3 = st.columns(3)
    m1.metric("Ángulo α (°)", f"{config.mask_alt:.1f}")
    m2.metric("Profundidad P (m)", f"{depth:.3f}")
    m3.metric("H eff (m)", f"{config.effective_shading_height_m:.2f}")

    side = (1.0 - CHART_WIDTH_RATIO) / 2.0
    _, chart_col, _ = st.columns([side, CHART_WIDTH_RATIO, side])
    with chart_col:
        st.pyplot(fig, use_container_width=True, clear_figure=False)

    _, btn_col, _ = st.columns([side, CHART_WIDTH_RATIO, side])
    with btn_col:
        png_bytes = figure_to_png_bytes(fig, dpi=EXPORT_DPI)
        basename = build_output_basename(config)
        st.download_button(
            label="Descargar PNG",
            data=png_bytes,
            file_name=f"{basename}.png",
            mime="image/png",
            use_container_width=False,
        )

    with st.expander("Informe de cobertura"):
        st.text(report)

    st.caption(CREDIT_LINE)


if __name__ == "__main__":
    main()
