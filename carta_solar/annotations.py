"""Diagrama en sección del dispositivo y resaltado del período crítico."""

from __future__ import annotations

import math

import numpy as np
from matplotlib.axes import Axes
from matplotlib.path import Path as MplPath
from matplotlib.patches import PathPatch, Rectangle

from carta_solar.config import DEVICE_VERTICAL_FIN, CartaSolarConfig
from carta_solar.critical import (
    MONTH_NAMES,
    MONTH_TO_DAY_OF_YEAR,
    collect_critical_samples,
    find_unprotected_samples,
    is_in_front_of_facade,
)
from carta_solar.devices.vertical_fin import (
    cut_angle_from_spacing,
    design_short_fins_from_config,
    find_unprotected_by_fin,
    spacing_from_count,
)
from carta_solar.devices.overhang import overhang_projection
from carta_solar.solar import solar_alt_az, solar_alt_az_at_clock, xy_from_alt_az

CRITICAL_PATH_COLOR = "#CC0000"
CRITICAL_PATH_WIDTH = 2.2
EXPOSED_MARKER_COLOR = "#D55E00"
PROTECTED_MARKER_COLOR = "#009E73"
EXPOSED_MARKER = "x"
PROTECTED_MARKER = "o"
CRITICAL_MONTH_FILL = "#87CEEB"
CRITICAL_MONTH_FILL_ALPHA = 0.28
CRITICAL_MONTH_PATH_COLOR = "#4DA6D9"


def draw_section_diagram(ax: Axes, config: CartaSolarConfig) -> None:
    """Panel constructivo según modo de dispositivo."""
    if config.device_mode == DEVICE_VERTICAL_FIN:
        draw_vertical_fin_plan(ax, config)
    else:
        draw_overhang_section(ax, config)


def draw_overhang_section(ax: Axes, config: CartaSolarConfig) -> None:
    """Corte vertical: antepecho, ventana, vano y alero con cotas reales."""
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    facade_title = f"Sección — fachada {config.facade_label}"

    h_s = config.sill_height_m
    h_v = config.window_height_m
    h_g = config.gap_to_overhang_m
    y_window_bottom = h_s
    y_window_top = h_s + h_v
    y_overhang = y_window_top + h_g

    if config.mask_alt is None:
        ax.set_xlim(-0.2, 2.5)
        ax.set_ylim(-0.2, max(y_overhang + 0.5, 2.0))
        ax.text(0.5, 0.5, "Calcular alero", ha="center", va="center", fontsize=11, color="#666666")
        ax.set_title(facade_title, fontsize=10, pad=8)
        return

    alpha = config.mask_alt
    depth = overhang_projection(config.effective_shading_height_m, alpha)

    dim_x = max(depth * 0.35, 0.12)
    margin_x = max(depth * 0.35, 0.12)
    margin_y = max(y_overhang * 0.08, 0.12)
    x_right = max(depth + margin_x, dim_x + 0.08)
    ax.set_xlim(-dim_x - 0.08, x_right)
    ax.set_ylim(-margin_y, y_overhang + margin_y)

    wall_x = 0.0
    wall_t = min(0.08, max(depth * 0.65, 0.012))
    ax.plot([wall_x, wall_x], [0, y_overhang], color="#333333", linewidth=3, solid_capstyle="butt")
    ax.plot([wall_x, x_right], [0, 0], color="#333333", linewidth=2)

    ax.add_patch(Rectangle((wall_x, 0), wall_t, y_window_bottom, facecolor="#CCCCCC", edgecolor="#333333"))
    ax.add_patch(
        Rectangle(
            (wall_x, y_window_bottom),
            wall_t,
            h_v,
            facecolor="#E8F4FC",
            edgecolor="#2266AA",
            linewidth=1.5,
        )
    )
    ax.add_patch(
        Rectangle(
            (wall_x, y_window_top),
            wall_t,
            h_g,
            facecolor="#CCCCCC",
            edgecolor="#333333",
        )
    )

    overhang_lw = 4 if depth < 0.15 else 3
    ax.plot(
        [wall_x, wall_x + depth],
        [y_overhang, y_overhang],
        color="#555555",
        linewidth=overhang_lw,
        solid_capstyle="butt",
    )
    drop = min(0.08, h_v * 0.06)
    ax.plot(
        [wall_x + depth, wall_x + depth],
        [y_overhang, y_overhang - drop],
        color="#555555",
        linewidth=2,
    )

    ax.plot(
        [wall_x + depth, wall_x],
        [y_overhang, y_window_bottom],
        color="#CC0000",
        linewidth=1.4,
        linestyle="--",
    )
    arc_r = min(y_overhang - y_window_bottom, max(depth, 0.05)) * 0.25
    arc_t = np.linspace(0, math.radians(alpha), 24)
    ax.plot(
        wall_x + arc_r * np.sin(arc_t),
        y_window_bottom + arc_r * (1 - np.cos(arc_t)),
        color="#CC0000",
        linewidth=1.4,
    )

    def dim_v(x: float, y0: float, y1: float, label: str) -> None:
        ax.annotate(
            "",
            xy=(x, y1),
            xytext=(x, y0),
            arrowprops=dict(arrowstyle="<->", color="#444444", lw=0.8),
        )
        ax.text(x - 0.04, (y0 + y1) / 2, label, ha="right", va="center", fontsize=8)

    dim_v(dim_x, 0, y_window_bottom, f"h_s\n{h_s:g} m")
    dim_v(dim_x, y_window_bottom, y_window_top, f"h_v\n{h_v:g} m")
    dim_v(dim_x, y_window_top, y_overhang, f"h_g\n{h_g:g} m")
    p_y = y_overhang + margin_y * 0.35
    ax.annotate(
        "",
        xy=(depth, p_y),
        xytext=(wall_x, p_y),
        arrowprops=dict(arrowstyle="<->", color="#444444", lw=0.8),
    )
    ax.text(
        depth / 2 if depth > 0.02 else depth + margin_x * 0.3,
        p_y + margin_y * 0.15,
        f"P = {depth:.3f} m",
        ha="center",
        fontsize=9,
        fontweight="bold",
    )
    ax.text(
        wall_x + max(depth, arc_r) * 0.6,
        y_window_bottom + arc_r * 1.6,
        f"α = {alpha:.1f}°",
        fontsize=9,
        color="#CC0000",
    )
    ax.set_title(facade_title, fontsize=10, pad=8)


def draw_vertical_fin_plan(ax: Axes, config: CartaSolarConfig) -> None:
    """
    Planta esquemática para arquitectos: muro, vano y banco de aletas cortas
    con separación, proyección D y flecha de rotación.
    """
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    title = f"Planta — fachada {config.facade_label} (aletas cortas)"
    w = config.window_width_m

    if config.mask_fin_angle is None and config.fin_count is None:
        ax.set_xlim(-0.5, 2.5)
        ax.set_ylim(-0.5, 2.0)
        ax.text(
            1.0,
            0.7,
            "Calcular aletas",
            ha="center",
            va="center",
            fontsize=11,
            color="#666666",
        )
        ax.set_title(title, fontsize=10, pad=8)
        return

    if config.fin_count is not None and config.fin_spacing_m is not None:
        n_fins = config.fin_count
        spacing = config.fin_spacing_m
        depth = config.fin_depth_m
        rotation = config.fin_rotation_deg
        cut = cut_angle_from_spacing(depth, spacing)
    else:
        design = design_short_fins_from_config(config)
        n_fins = design.n_fins
        spacing = design.spacing_m
        depth = design.depth_m
        rotation = design.rotation_deg
        cut = design.cut_angle_deg

    wall_t = 0.12
    # Extensión lateral por rotación de aletas
    rot_rad = math.radians(rotation)
    fin_extent_x = abs(depth * math.sin(rot_rad)) + 0.08
    margin_x = max(spacing * 0.35, fin_extent_x, 0.25)
    margin_y = max(depth * 0.45, 0.25)
    ax.set_xlim(-margin_x - wall_t, w + margin_x + wall_t)
    ax.set_ylim(-margin_y, depth + margin_y)

    # Muro (tramos laterales al vano)
    wall_y0, wall_y1 = -0.06, 0.06
    ax.add_patch(
        Rectangle(
            (-wall_t - margin_x * 0.5, wall_y0),
            wall_t + margin_x * 0.5,
            wall_y1 - wall_y0,
            facecolor="#888888",
            edgecolor="#333333",
        )
    )
    ax.add_patch(
        Rectangle(
            (w, wall_y0),
            wall_t + margin_x * 0.5,
            wall_y1 - wall_y0,
            facecolor="#888888",
            edgecolor="#333333",
        )
    )
    # Línea de fachada / vano
    ax.plot([0, w], [0, 0], color="#2266AA", linewidth=3, solid_capstyle="butt")
    ax.text(w / 2, -margin_y * 0.55, f"W = {w:g} m", ha="center", fontsize=8)

    # Posiciones de centros (jambas + intermedias)
    if n_fins < 2:
        n_fins = 2
        spacing = spacing_from_count(w, n_fins)
    xs = [i * spacing for i in range(n_fins)]
    # Ajuste numérico: última aleta en el jamba derecho
    xs[-1] = w

    cos_r = math.cos(rot_rad)
    sin_r = math.sin(rot_rad)
    for x0 in xs:
        # Aleta: desde el plano de fachada hacia afuera, rotada θ sobre su eje
        x1 = x0 + depth * sin_r
        y1 = depth * cos_r
        # Si la rotación hace que y1 sea negativo (θ≈±90), forzar saliente
        if y1 < depth * 0.15:
            y1 = depth * abs(cos_r) if abs(cos_r) > 0.15 else depth * 0.15
            x1 = x0 + depth * sin_r
        ax.plot(
            [x0, x1],
            [0.0, max(y1, depth * 0.2)],
            color="#555555",
            linewidth=3.2,
            solid_capstyle="butt",
            zorder=3,
        )

    # Cota de separación entre las dos primeras aletas
    if n_fins >= 2 and spacing > 0.05:
        s_y = -margin_y * 0.28
        ax.annotate(
            "",
            xy=(xs[1], s_y),
            xytext=(xs[0], s_y),
            arrowprops=dict(arrowstyle="<->", color="#444444", lw=0.8),
        )
        ax.text(
            (xs[0] + xs[1]) / 2,
            s_y - margin_y * 0.08,
            f"S = {spacing * 100:.0f} cm",
            ha="center",
            fontsize=8,
            color="#333333",
        )

    # Cota de profundidad D
    d_x = -margin_x * 0.55
    tip_y = depth * abs(math.cos(rot_rad)) if abs(math.cos(rot_rad)) > 0.2 else depth * 0.85
    ax.annotate(
        "",
        xy=(d_x, tip_y),
        xytext=(d_x, 0.0),
        arrowprops=dict(arrowstyle="<->", color="#444444", lw=0.8),
    )
    ax.text(
        d_x - 0.02,
        tip_y / 2,
        f"D = {depth:.2f} m",
        ha="right",
        va="center",
        fontsize=8,
        fontweight="bold",
    )

    # Flecha / arco de rotación sobre una aleta intermedia (o la primera)
    pivot_i = min(1, n_fins - 1)
    px = xs[pivot_i]
    arc_r = min(depth, spacing) * 0.4
    if abs(rotation) >= 0.5:
        arc_t = np.linspace(0.0, rot_rad, 20)
        ax.plot(
            px + arc_r * np.sin(arc_t),
            arc_r * np.cos(arc_t),
            color="#CC0000",
            linewidth=1.3,
        )
        ax.annotate(
            "",
            xy=(px + depth * 0.55 * sin_r, depth * 0.55 * abs(cos_r) + 0.02),
            xytext=(px, depth * 0.55),
            arrowprops=dict(arrowstyle="->", color="#CC0000", lw=1.2),
        )
        ax.text(
            px + spacing * 0.15,
            depth * 0.72,
            f"rot. {rotation:+.0f}°",
            color="#CC0000",
            fontsize=8,
        )
    else:
        ax.text(
            px + spacing * 0.1,
            depth * 0.55,
            "0° (de canto)",
            color="#666666",
            fontsize=8,
        )

    ax.text(
        w / 2,
        depth + margin_y * 0.35,
        f"N = {n_fins} aletas  ·  corte en planta ≈ {cut:.1f}°",
        ha="center",
        fontsize=8,
        color="#333333",
    )
    ax.set_title(title, fontsize=10, pad=8)


def draw_critical_months_highlight(ax: Axes, config: CartaSolarConfig) -> None:
    """Rellena en celeste translúcido las trayectorias de los meses a sombrear."""
    facade_az = config.facade_azimuth
    n_hours = 81 if config.is_preview else 241
    hours = np.linspace(4, 20, n_hours)
    for month in sorted(config.critical_months):
        day = MONTH_TO_DAY_OF_YEAR[month]
        path_points: list[tuple[float, float]] = []
        for hour in hours:
            alt, az = solar_alt_az_at_clock(
                config.lat,
                config.lon,
                day,
                float(hour),
                use_civil_hours=config.use_civil_hours,
                timezone_utc_hours=config.timezone_utc_offset,
            )
            if alt <= 0:
                continue
            x, y = xy_from_alt_az(alt, az)
            if is_in_front_of_facade(az, facade_az):
                path_points.append((x, y))

        if len(path_points) < 2:
            continue

        xs = [p[0] for p in path_points]
        ys = [p[1] for p in path_points]
        # Cerrar hacia el origen proyectado sobre el diámetro de fachada ≈ cenit-lado
        polygon_x = xs + [0.0]
        polygon_y = ys + [0.0]
        patch = PathPatch(
            MplPath(np.column_stack([polygon_x, polygon_y])),
            facecolor=CRITICAL_MONTH_FILL,
            edgecolor=CRITICAL_MONTH_PATH_COLOR,
            linewidth=0.8,
            alpha=CRITICAL_MONTH_FILL_ALPHA,
            zorder=2.2,
        )
        ax.add_patch(patch)

        alt_noon, az_noon = solar_alt_az(config.lat, day, 12.0)
        if alt_noon > 0:
            x_n, y_n = xy_from_alt_az(alt_noon, az_noon)
            ax.plot(
                x_n,
                y_n,
                marker="o",
                markersize=5,
                color=CRITICAL_MONTH_PATH_COLOR,
                markeredgecolor="white",
                markeredgewidth=0.5,
                linestyle="none",
                zorder=3.5,
            )
            r_n = float(np.hypot(x_n, y_n))
            scale = max(1.025, 1.02) / r_n if r_n < 1.0 else 1.025
            ax.text(
                x_n * scale,
                y_n * scale,
                MONTH_NAMES[month],
                fontsize=7,
                color="#1A5276",
                ha="center",
                va="bottom" if y_n >= 0 else "top",
                zorder=10,
            )


def draw_critical_overlays(ax: Axes, config: CartaSolarConfig) -> None:
    """Resalta trayectorias y puntos del período crítico."""
    if not config.highlight_critical_period:
        return

    facade_az = config.facade_azimuth
    samples = collect_critical_samples(
        config.lat,
        config.critical_months,
        config.critical_hour_start,
        config.critical_hour_end,
        facade_az=facade_az,
        lon=config.lon,
        use_civil_hours=config.use_civil_hours,
        timezone_utc_hours=config.timezone_utc_offset,
    )
    if not samples:
        return

    if config.device_mode == DEVICE_VERTICAL_FIN:
        unprotected = {
            (s.month, round(s.hour, 2))
            for s in find_unprotected_by_fin(samples, config.mask_fin_angle, facade_az)
        }
    else:
        unprotected = {
            (s.month, round(s.hour, 2))
            for s in find_unprotected_samples(
                samples, config.mask_alt, facade_az=facade_az
            )
        }

    step = 0.5 if config.is_preview else 0.25
    hours = np.arange(config.critical_hour_start, config.critical_hour_end + 0.01, step)
    for month in sorted(config.critical_months):
        day = MONTH_TO_DAY_OF_YEAR[month]
        xs, ys = [], []
        for hour in hours:
            alt, az = solar_alt_az_at_clock(
                config.lat,
                config.lon,
                day,
                float(hour),
                use_civil_hours=config.use_civil_hours,
                timezone_utc_hours=config.timezone_utc_offset,
            )
            if alt <= 0:
                continue
            x, y = xy_from_alt_az(alt, az)
            if is_in_front_of_facade(az, facade_az):
                xs.append(x)
                ys.append(y)
        if len(xs) >= 2:
            ax.plot(
                xs,
                ys,
                color=CRITICAL_PATH_COLOR,
                linewidth=CRITICAL_PATH_WIDTH,
                zorder=4,
                alpha=0.85,
            )

    for sample in samples:
        key = (sample.month, round(sample.hour, 2))
        exposed = key in unprotected
        ax.plot(
            sample.x,
            sample.y,
            marker=EXPOSED_MARKER if exposed else PROTECTED_MARKER,
            markersize=4.0 if exposed else 3.5,
            color=EXPOSED_MARKER_COLOR if exposed else PROTECTED_MARKER_COLOR,
            linestyle="none",
            zorder=5,
            alpha=0.9,
        )

    ax.plot([], [], marker=PROTECTED_MARKER, color=PROTECTED_MARKER_COLOR, linestyle="none", label="Protegido")
    ax.plot([], [], marker=EXPOSED_MARKER, color=EXPOSED_MARKER_COLOR, linestyle="none", label="Expuesto")
    ax.legend(loc="lower left", fontsize=7, framealpha=0.9)
