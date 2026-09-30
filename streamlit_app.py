"""Versión web de Carta Solar — dispositivos por azimut (Streamlit)."""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import streamlit as st

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
    NEAR_NORMAL_DEG,
    describe_fin_design,
    find_unprotected_by_fin,
    fin_depth_from_angle,
    suggested_critical_hours,
)
from carta_solar.overhang import apply_computed_mask, overhang_projection
from carta_solar.plot import build_output_basename, generate_carta_solar
from carta_solar.solar import estimate_timezone_utc

WEB_FIGSIZE = (12.0, 6.0)
WEB_DISPLAY_DPI = 120
EXPORT_DPI = 300
CHART_WIDTH_RATIO = 0.75

FACADE_PRESETS = {
    "Norte (0°)": 0.0,
    "Este (90°)": 90.0,
    "Sur (180°)": 180.0,
    "Oeste (270°)": 270.0,
    "Personalizado": None,
}


@dataclass(frozen=True)
class AppState:
    site_name: str
    lat: float
    lon: float
    sill_height_m: float
    window_height_m: float
    gap_to_overhang_m: float
    window_width_m: float
    critical_months: frozenset[int]
    critical_hour_start: int
    critical_hour_end: int
    hour_start: int
    hour_end: int
    highlight_critical_period: bool
    use_civil_hours: bool = True
    timezone_utc_offset: float | None = None
    device_mode: str = DEVICE_OVERHANG
    facade_azimuth_override: float | None = None
    fin_arrangement: str = "bilateral"


def build_config_from_state(
    state: AppState,
    *,
    for_web: bool = False,
) -> CartaSolarConfig:
    web_kwargs = (
        {
            "figsize": WEB_FIGSIZE,
            "dpi": WEB_DISPLAY_DPI,
            "chart_detail": "preview",
        }
        if for_web
        else {}
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
        window_width_m=state.window_width_m,
        critical_months=state.critical_months,
        critical_hour_start=state.critical_hour_start,
        critical_hour_end=state.critical_hour_end,
        highlight_critical_period=state.highlight_critical_period,
        use_civil_hours=state.use_civil_hours,
        timezone_utc_offset=state.timezone_utc_offset,
        device_mode=state.device_mode,
        facade_azimuth_override=state.facade_azimuth_override,
        fin_arrangement=state.fin_arrangement,
        **web_kwargs,
    )


def figure_to_png_bytes(fig: plt.Figure, *, dpi: int = 300) -> bytes:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=dpi, bbox_inches="tight")
    buffer.seek(0)
    return buffer.getvalue()


def should_recalculate(
    state: AppState,
    previous_state: AppState | None,
    *,
    force: bool = False,
    has_figure: bool = False,
) -> bool:
    if force or not has_figure:
        return True
    return previous_state != state


def suggested_mode_for_azimuth(facade_az: float) -> str:
    """Sugiere vertical en E/O (±45° alrededor de 90/270)."""
    az = facade_az % 360.0
    dist_e = min(abs(az - 90.0), 360.0 - abs(az - 90.0))
    dist_w = min(abs(az - 270.0), 360.0 - abs(az - 270.0))
    if dist_e <= 45.0 or dist_w <= 45.0:
        return DEVICE_VERTICAL_FIN
    return DEVICE_OVERHANG


def _default_state() -> AppState:
    return AppState(
        site_name="Ñacuñán",
        lat=-34.0333,
        lon=-67.9167,
        sill_height_m=0.9,
        window_height_m=1.2,
        gap_to_overhang_m=0.3,
        window_width_m=1.5,
        critical_months=DEFAULT_CRITICAL_MONTHS,
        critical_hour_start=10,
        critical_hour_end=18,
        hour_start=5,
        hour_end=19,
        highlight_critical_period=True,
        use_civil_hours=True,
        timezone_utc_offset=-3.0,
        device_mode=DEVICE_OVERHANG,
        facade_azimuth_override=None,
        fin_arrangement="bilateral",
    )


def _sidebar_state() -> AppState:
    st.sidebar.header("Modo de cálculo")
    mode_label = st.sidebar.radio(
        "Dispositivo",
        options=["Alero horizontal", "Parasol vertical"],
        index=0,
        help="En fachadas Este/Oeste el parasol vertical suele ser más eficaz.",
    )
    device_mode = (
        DEVICE_VERTICAL_FIN if mode_label.startswith("Parasol") else DEVICE_OVERHANG
    )

    st.sidebar.header("Ubicación")
    site_name = st.sidebar.text_input(
        "Nombre del sitio", value="Ñacuñán", max_chars=SITE_NAME_MAX_LEN
    )
    lat = st.sidebar.number_input(
        "Latitud (Sur = −)", value=-34.0333, min_value=-90.0, max_value=90.0, format="%.4f"
    )
    lon = st.sidebar.number_input(
        "Longitud (Oeste = −)",
        value=-67.9167,
        min_value=-180.0,
        max_value=180.0,
        format="%.4f",
        help="Convierte horas civiles → solares (huso + ecuación del tiempo).",
    )

    auto_az = facade_azimuth_for_lat(float(lat))
    preset = st.sidebar.selectbox(
        "Azimut de fachada",
        options=list(FACADE_PRESETS.keys()),
        index=0 if abs(auto_az) < 1 else (2 if abs(auto_az - 180) < 1 else 4),
    )
    if FACADE_PRESETS[preset] is None:
        facade_az = st.sidebar.number_input(
            "Azimut personalizado (°)",
            value=float(auto_az),
            min_value=0.0,
            max_value=359.9,
            step=5.0,
        )
        facade_override = float(facade_az)
    else:
        facade_override = float(FACADE_PRESETS[preset])

    suggested = suggested_mode_for_azimuth(facade_override)
    if suggested != device_mode:
        tip = "parasol vertical" if suggested == DEVICE_VERTICAL_FIN else "alero horizontal"
        st.sidebar.info(f"Sugerencia bioclimática para esta orientación: **{tip}**.")

    st.sidebar.caption(
        f"Fachada: **{facade_label_for_azimuth(facade_override)}** ({facade_override:g}°)"
    )

    use_civil_hours = st.sidebar.checkbox("Horas civiles (reloj local)", value=True)
    timezone_utc_offset = st.sidebar.number_input(
        "Huso UTC (político)",
        value=-3.0,
        min_value=-12.0,
        max_value=14.0,
        step=1.0,
        format="%.0f",
        disabled=not use_civil_hours,
    )
    tz_geo = estimate_timezone_utc(float(lon))
    st.sidebar.caption(f"Huso geográfico aprox.: UTC{tz_geo:+g}")

    st.sidebar.header("Medidas (m)")
    sill_height_m = st.sidebar.number_input(
        "Antepecho (piso → ventana)", value=0.9, min_value=0.0, step=0.05
    )
    window_height_m = st.sidebar.number_input(
        "Altura ventana", value=1.2, min_value=0.01, step=0.05
    )
    gap_to_overhang_m = st.sidebar.number_input(
        "Vano (cierre ventana → alero)", value=0.3, min_value=0.0, step=0.05
    )
    window_width_m = st.sidebar.number_input(
        "Ancho ventana (aletas)",
        value=1.5,
        min_value=0.1,
        step=0.1,
        disabled=device_mode != DEVICE_VERTICAL_FIN,
    )
    fin_arrangement = "bilateral"
    if device_mode == DEVICE_VERTICAL_FIN:
        arr = st.sidebar.radio("Disposición de aletas", ["Ambos lados", "Un solo lado"], index=0)
        fin_arrangement = "bilateral" if arr.startswith("Ambos") else "single"

    default_months = sorted(default_critical_months_for_lat(float(lat)))
    def_h1, def_h2 = suggested_critical_hours(facade_override)
    facade_hours_key = round(float(facade_override), 1)
    if st.session_state.get("_crit_hours_facade") != facade_hours_key:
        st.session_state["crit_hour_start"] = def_h1
        st.session_state["crit_hour_end"] = def_h2
        st.session_state["_crit_hours_facade"] = facade_hours_key

    st.sidebar.header("Período crítico")
    st.sidebar.caption(
        f"Verano local: {', '.join(MONTH_NAMES[m] for m in default_months)}"
    )
    month_options = st.sidebar.multiselect(
        "Meses críticos",
        options=list(range(1, 13)),
        default=default_months,
        format_func=lambda m: MONTH_NAMES[m],
    )
    selected_months = set(month_options)
    crit_h1, crit_h2 = st.sidebar.columns(2)
    with crit_h1:
        critical_hour_start = st.number_input(
            "Hora crítica inicio",
            min_value=0,
            max_value=23,
            step=1,
            key="crit_hour_start",
        )
    with crit_h2:
        critical_hour_end = st.number_input(
            "Hora crítica fin",
            min_value=1,
            max_value=23,
            step=1,
            key="crit_hour_end",
        )
    highlight_critical_period = st.sidebar.checkbox(
        "Resaltar período crítico en carta", value=True
    )

    st.sidebar.header("Carta")
    h1, h2 = st.sidebar.columns(2)
    with h1:
        hour_start = st.number_input(
            "Hora inicio (líneas)", value=5, min_value=0, max_value=23, step=1
        )
    with h2:
        hour_end = st.number_input(
            "Hora fin (líneas)", value=19, min_value=1, max_value=23, step=1
        )

    if not selected_months:
        selected_months = set(default_critical_months_for_lat(float(lat)))

    return AppState(
        site_name=(site_name.strip() or "Sitio")[:SITE_NAME_MAX_LEN],
        lat=float(lat),
        lon=float(lon),
        sill_height_m=float(sill_height_m),
        window_height_m=float(window_height_m),
        gap_to_overhang_m=float(gap_to_overhang_m),
        window_width_m=float(window_width_m),
        critical_months=frozenset(selected_months),
        critical_hour_start=int(critical_hour_start),
        critical_hour_end=int(critical_hour_end),
        hour_start=int(hour_start),
        hour_end=int(hour_end),
        highlight_critical_period=highlight_critical_period,
        use_civil_hours=bool(use_civil_hours),
        timezone_utc_offset=float(timezone_utc_offset) if use_civil_hours else None,
        device_mode=device_mode,
        facade_azimuth_override=facade_override,
        fin_arrangement=fin_arrangement,
    )


def _close_previous_figure() -> None:
    prev = st.session_state.get("figure")
    if prev is not None:
        plt.close(prev)


def _build_report(config: CartaSolarConfig) -> tuple[str, float | None, float | None, int | None]:
    """Retorna (report, metric_angle, metric_depth, limiting_month)."""
    samples = collect_critical_samples(
        config.lat,
        config.critical_months,
        config.critical_hour_start,
        config.critical_hour_end,
        facade_az=config.facade_azimuth,
        lon=config.lon,
        use_civil_hours=config.use_civil_hours,
        timezone_utc_hours=config.timezone_utc_offset,
    )
    if config.device_mode == DEVICE_VERTICAL_FIN:
        design = describe_fin_design(config)
        beta = design.beta_deg
        bilateral = config.fin_arrangement != "single"
        depth = fin_depth_from_angle(
            config.window_width_m, beta, bilateral=bilateral
        )
        month = design.limiting_month
        unprotected = find_unprotected_by_fin(samples, beta, config.facade_azimuth)
        total = len(samples)
        covered = total - len(unprotected)
        pct = 100.0 * covered / total if total else 0.0
        report = (
            f"β = {beta:.1f}° (percentil P{design.percentile:g} de |γ|, "
            f"mes {MONTH_NAMES.get(month or 0, '—')}).\n"
        )
        if design.beta_left_deg is not None or design.beta_right_deg is not None:
            bl = f"{design.beta_left_deg:.1f}°" if design.beta_left_deg is not None else "—"
            br = f"{design.beta_right_deg:.1f}°" if design.beta_right_deg is not None else "—"
            report += f"β izq/der (ref. SOL-AR): {bl} / {br}.\n"
        if design.capped_by_max_depth:
            report += "β limitado por profundidad máxima constructiva.\n"
        report += (
            f"Rango horario {total} posiciones: {covered}/{total} bajo aletas ({pct:.0f}%).\n"
            f"Sol casi normal (|γ| < {NEAR_NORMAL_DEG:g}°): {design.n_near_normal} "
            f"de {design.n_frontal} frontales — no sombreable solo con aletas.\n"
        )
        if design.n_near_normal > 0 and design.n_near_normal >= 0.25 * max(design.n_frontal, 1):
            report += (
                "Aviso: mucha insolación frontal; considerá combinar con alero "
                "u otro dispositivo (flujo típico SOL-AR).\n"
            )
        if not unprotected:
            report += "Período horario completamente cubierto (criterio |γ| ≥ β)."
        else:
            report += "Posiciones fuera de aletas (sol expuesto):\n"
            for s in unprotected[:8]:
                report += f"  • {s.label()}\n"
        return report, beta, depth, month

    alpha, samples2, month = compute_required_alpha(
        config.lat,
        config.critical_months,
        config.critical_hour_start,
        config.critical_hour_end,
        facade_az=config.facade_azimuth,
        lon=config.lon,
        use_civil_hours=config.use_civil_hours,
        timezone_utc_hours=config.timezone_utc_offset,
    )
    report = format_exposure_report(
        samples2,
        config.mask_alt,
        limiting_month=month,
        facade_az=config.facade_azimuth,
    )
    depth = (
        overhang_projection(config.effective_shading_height_m, config.mask_alt)
        if config.mask_alt
        else None
    )
    return report, config.mask_alt, depth, month


def main() -> None:
    st.set_page_config(page_title="Carta Solar — Parasoles", layout="wide")
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] {
            width: 18rem !important;
            min-width: 18rem !important;
        }
        .block-container { padding-top: 1rem; max-width: none; }
        [data-testid="stMetricValue"] { font-size: 1.35rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("Carta Solar — Parasoles por azimut")
    st.caption(f"{AUTHORS}  |  {INSTITUTION}")

    logos = available_logos()
    if logos:
        cols = st.columns(len(logos))
        for col, logo_path in zip(cols, logos, strict=False):
            col.image(str(logo_path), width=120)

    state = _sidebar_state()
    calc = st.sidebar.button("Calcular", type="primary", use_container_width=True)
    previous_state: AppState | None = st.session_state.get("app_state")
    needs_recalc = should_recalculate(
        state,
        previous_state,
        force=calc,
        has_figure="figure" in st.session_state,
    )

    if needs_recalc:
        try:
            base_config = build_config_from_state(state, for_web=True)
            config = apply_computed_mask(base_config)
            _close_previous_figure()
            fig = generate_carta_solar(config)
            report, angle, depth, _month = _build_report(config)
            st.session_state["figure"] = fig
            st.session_state["config"] = config
            st.session_state["report"] = report
            st.session_state["metric_angle"] = angle
            st.session_state["metric_depth"] = depth
            st.session_state["app_state"] = state
            st.session_state.pop("png_bytes", None)
        except ValueError as exc:
            st.error(str(exc))
            return
        except Exception:
            st.error("No se pudo calcular. Revisá los parámetros e intentá de nuevo.")
            return

    if "figure" not in st.session_state:
        st.info("Completá los parámetros; la carta se actualiza al cambiarlos.")
        return

    config: CartaSolarConfig = st.session_state["config"]
    fig: plt.Figure = st.session_state["figure"]
    report: str = st.session_state["report"]
    angle = st.session_state.get("metric_angle")
    depth = st.session_state.get("metric_depth")

    if config.device_mode == DEVICE_VERTICAL_FIN:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Ángulo β (°)", f"{angle:.1f}" if angle else "—")
        m2.metric("Profundidad D (m)", f"{depth:.3f}" if depth else "—")
        m3.metric("Ancho W (m)", f"{config.window_width_m:.2f}")
        m4.metric("Fachada", f"{config.facade_label} ({config.facade_azimuth:g}°)")
        st.caption(
            "Parasol vertical: dimensiona aletas para cortar el sol con |γ| ≥ β. "
            "Ideal en Este/Oeste; el alero solo ayuda con sol alto frente a la fachada."
        )
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Ángulo α (°)", f"{angle:.1f}" if angle else "—")
        m2.metric("Profundidad P (m)", f"{depth:.3f}" if depth else "—")
        m3.metric("H eff (m)", f"{config.effective_shading_height_m:.2f}")
        m4.metric("Fachada", f"{config.facade_label} ({config.facade_azimuth:g}°)")
        st.caption(
            "Alero horizontal: α = mín. ángulo de perfil ε del período crítico. "
            "Eficaz en fachadas Norte/Sur; en E/O considerá parasol vertical."
        )

    side = (1.0 - CHART_WIDTH_RATIO) / 2.0
    _, chart_col, _ = st.columns([side, CHART_WIDTH_RATIO, side])
    with chart_col:
        st.pyplot(fig, use_container_width=True, clear_figure=False)

    _, btn_col, _ = st.columns([side, CHART_WIDTH_RATIO, side])
    with btn_col:
        # PNG lazy: solo al pedir descarga (export a alta densidad)
        if st.button("Preparar PNG alta resolución"):
            from dataclasses import replace

            export_cfg = replace(
                config, chart_detail="full", dpi=EXPORT_DPI, figsize=(16.0, 8.0)
            )
            export_fig = generate_carta_solar(export_cfg)
            st.session_state["png_bytes"] = figure_to_png_bytes(export_fig, dpi=EXPORT_DPI)
            st.session_state["png_name"] = f"{build_output_basename(config)}.png"
            plt.close(export_fig)

        png_bytes = st.session_state.get("png_bytes")
        if png_bytes:
            st.download_button(
                label="Descargar PNG",
                data=png_bytes,
                file_name=st.session_state.get("png_name") or "carta_solar.png",
                mime="image/png",
            )
        else:
            st.caption("Vista previa rápida. Pulsá «Preparar PNG» para exportar a 300 dpi.")

    with st.expander("Informe de cobertura"):
        st.text(report)

    st.caption(CREDIT_LINE)


if __name__ == "__main__":
    main()
