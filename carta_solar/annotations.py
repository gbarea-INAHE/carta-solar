"""Diagrama en sección del alero y resaltado del período crítico."""

from __future__ import annotations

import math

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.path import Path as MplPath
from matplotlib.patches import PathPatch, Rectangle

from carta_solar.config import CartaSolarConfig
from carta_solar.critical import (
    MONTH_NAMES,
    MONTH_TO_DAY_OF_YEAR,
    collect_critical_samples,
    find_unprotected_samples,
    is_in_northern_sector,
)
from carta_solar.overhang import overhang_projection
from carta_solar.solar import solar_alt_az, xy_from_alt_az

CRITICAL_PATH_COLOR = "#CC0000"
CRITICAL_PATH_WIDTH = 2.2
EXPOSED_MARKER_COLOR = "#FF2200"
PROTECTED_MARKER_COLOR = "#228822"
CRITICAL_MONTH_FILL = "#87CEEB"
CRITICAL_MONTH_FILL_ALPHA = 0.28
CRITICAL_MONTH_PATH_COLOR = "#4DA6D9"


def draw_section_diagram(ax: Axes, config: CartaSolarConfig) -> None:
    """Corte vertical: antepecho, ventana, vano y alero con cotas reales."""
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")

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
        ax.set_title("Sección — fachada Norte", fontsize=10, pad=8)
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
    ax.set_title("Sección — fachada Norte", fontsize=10, pad=8)


def draw_critical_months_highlight(ax: Axes, config: CartaSolarConfig) -> None:
    """Rellena en celeste translúcido las trayectorias de los meses a sombrear."""
    hours = np.linspace(4, 20, 241)
    for month in sorted(config.critical_months):
        day = MONTH_TO_DAY_OF_YEAR[month]
        path_points: list[tuple[float, float]] = []
        for hour in hours:
            alt, az = solar_alt_az(config.lat, day, float(hour))
            if alt <= 0:
                continue
            x, y = xy_from_alt_az(alt, az)
            if is_in_northern_sector(az, y):
                path_points.append((x, y))

        if len(path_points) < 2:
            continue

        xs = [p[0] for p in path_points]
        ys = [p[1] for p in path_points]
        polygon_x = xs + [xs[-1], xs[0]]
        polygon_y = ys + [0.0, 0.0]
        patch = PathPatch(
            MplPath(np.column_stack([polygon_x, polygon_y])),
            facecolor=CRITICAL_MONTH_FILL,
            edgecolor=CRITICAL_MONTH_PATH_COLOR,
            linewidth=0.8,
            alpha=CRITICAL_MONTH_FILL_ALPHA,
            zorder=2.2,
        )
        ax.add_patch(patch)

        alt_noon, _ = solar_alt_az(config.lat, day, 12.0)
        if alt_noon > 0:
            x_n, y_n = xy_from_alt_az(alt_noon, 0.0)
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

    samples = collect_critical_samples(
        config.lat,
        config.critical_months,
        config.critical_hour_start,
        config.critical_hour_end,
    )
    if not samples:
        return

    unprotected = {
        (s.month, round(s.hour, 2))
        for s in find_unprotected_samples(samples, config.mask_alt)
    }

    hours = np.arange(config.critical_hour_start, config.critical_hour_end + 0.01, 0.25)
    for month in sorted(config.critical_months):
        day = MONTH_TO_DAY_OF_YEAR[month]
        xs, ys = [], []
        for hour in hours:
            alt, az = solar_alt_az(config.lat, day, float(hour))
            if alt <= 0:
                continue
            x, y = xy_from_alt_az(alt, az)
            if is_in_northern_sector(az, y):
                xs.append(x)
                ys.append(y)
        if len(xs) >= 2:
            ax.plot(xs, ys, color=CRITICAL_PATH_COLOR, linewidth=CRITICAL_PATH_WIDTH, zorder=4, alpha=0.85)

    for sample in samples:
        key = (sample.month, round(sample.hour, 2))
        color = EXPOSED_MARKER_COLOR if key in unprotected else PROTECTED_MARKER_COLOR
        ax.plot(
            sample.x,
            sample.y,
            marker="o",
            markersize=3.5,
            color=color,
            linestyle="none",
            zorder=5,
            alpha=0.9,
        )
