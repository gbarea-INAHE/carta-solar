"""Transportador de máscara estilo SOL-AR (arcos circulares rotables).

Geometría del transportador en carta estereográfica
---------------------------------------------------
Cada curva de ángulo α NO es un círculo de altitud ni alt = α×cos(δ).
Es un arco de circunferencia en el plano de proyección que, en marco de
fachada Norte:

  1. Pasa por Oeste (-1, 0) y Este (1, 0) en el horizonte.
  2. Corta el meridiano Norte en (0, r(α)), con r(α) = tan((90°-α)/2).

Para un azimut de fachada arbitrario se rota el conjunto por −facade_az
alrededor del cenit, de modo que el pico del arco apunta a la normal.
"""

from __future__ import annotations

import numpy as np
from matplotlib.axes import Axes
from matplotlib.path import Path
from matplotlib.patches import PathPatch

from carta_solar.solar import r_from_alt

GRID_COLOR = "#CC0000"
GRID_LINEWIDTH = 0.8
ACTIVE_LINE_COLOR = "#555555"
ACTIVE_LINEWIDTH = 2.5
FILL_COLOR = "#888888"
FILL_ALPHA = 0.25
FIN_FILL_COLOR = "#6B8E9B"
FIN_FILL_ALPHA = 0.28
EW_LINE_COLOR = "#000000"
EW_LINEWIDTH = 1.0

PROTRACTOR_ZORDER = 2.5
CURVE_SAMPLE_POINTS = 120

WEST = (-1.0, 0.0)
EAST = (1.0, 0.0)


def rotate_points(points: np.ndarray, facade_az: float) -> np.ndarray:
    """Rota puntos del marco Norte al azimut de fachada (θ = −facade_az)."""
    theta = np.radians(-float(facade_az) % 360.0)
    c, s = np.cos(theta), np.sin(theta)
    x = points[:, 0]
    y = points[:, 1]
    return np.column_stack([x * c - y * s, x * s + y * c])


def circle_params_for_alpha(alpha: float) -> tuple[float, float, float]:
    """
    Centro (0, y_c), radio R y cota de pico h de la circunferencia del arco α
    en coordenadas de fachada Norte (pico en +y).
    """
    h = r_from_alt(alpha)
    if h <= 0:
        raise ValueError("El ángulo α debe ser mayor que 0°.")

    y_c = (h * h - 1.0) / (2.0 * h)
    radius = float(np.sqrt(1.0 + y_c * y_c))
    return y_c, radius, h


def alpha_curve_points(
    alpha: float,
    *,
    num_points: int = CURVE_SAMPLE_POINTS,
    facade_az: float = 0.0,
) -> np.ndarray:
    """Arco del transportador rotado hacia la fachada."""
    y_c, radius, _ = circle_params_for_alpha(alpha)

    theta_w = float(np.arctan2(-y_c, -1.0))
    theta_e = float(np.arctan2(-y_c, 1.0))

    thetas = np.linspace(theta_w, theta_e, num_points)
    x = radius * np.cos(thetas)
    y = y_c + radius * np.sin(thetas)
    local = np.column_stack([x, y])
    return rotate_points(local, facade_az)


def build_shaded_region_vertices(
    alpha: float,
    *,
    num_points: int = CURVE_SAMPLE_POINTS,
    facade_az: float = 0.0,
) -> np.ndarray:
    """Polígono cerrado: arco α + diámetro de fachada (rotado)."""
    curve = alpha_curve_points(alpha, num_points=num_points, facade_az=facade_az)
    diameter = rotate_points(np.array([EAST, WEST]), facade_az)
    return np.vstack([curve, diameter])


def north_peak_y(alpha: float) -> float:
    """Cota y donde el arco α corta el meridiano Norte (fachada Norte)."""
    _, _, h = circle_params_for_alpha(alpha)
    return h


def facade_peak_xy(alpha: float, facade_az: float = 0.0) -> tuple[float, float]:
    """Punto donde el arco α corta el meridiano de la fachada."""
    peak = rotate_points(np.array([[0.0, north_peak_y(alpha)]]), facade_az)[0]
    return float(peak[0]), float(peak[1])


def draw_protractor_grid(
    ax: Axes,
    *,
    step: int = 10,
    alpha_min: int = 10,
    alpha_max: int = 80,
    color: str = GRID_COLOR,
    linewidth: float = GRID_LINEWIDTH,
    facade_az: float = 0.0,
) -> list:
    """Rejilla roja: arcos circulares α = 10°, 20°, … 80°."""
    lines = []
    for alpha in range(alpha_min, alpha_max + 1, step):
        points = alpha_curve_points(float(alpha), facade_az=facade_az)
        (line,) = ax.plot(
            points[:, 0],
            points[:, 1],
            color=color,
            linewidth=linewidth,
            zorder=PROTRACTOR_ZORDER,
        )
        lines.append(line)
    return lines


def draw_alpha_mask(
    ax: Axes,
    alpha: float,
    *,
    line_color: str = ACTIVE_LINE_COLOR,
    line_width: float = ACTIVE_LINEWIDTH,
    fill_color: str = FILL_COLOR,
    fill_alpha: float = FILL_ALPHA,
    facade_az: float = 0.0,
) -> tuple[PathPatch, object]:
    """Curva α activa (gris) y relleno semitransparente bajo el arco."""
    vertices = build_shaded_region_vertices(alpha, facade_az=facade_az)
    patch = PathPatch(
        Path(vertices),
        facecolor=fill_color,
        edgecolor="none",
        alpha=fill_alpha,
        zorder=PROTRACTOR_ZORDER,
    )
    ax.add_patch(patch)

    curve = alpha_curve_points(alpha, facade_az=facade_az)
    (line,) = ax.plot(
        curve[:, 0],
        curve[:, 1],
        color=line_color,
        linewidth=line_width,
        zorder=PROTRACTOR_ZORDER + 0.1,
    )
    return patch, line


def draw_facade_diameter(ax: Axes, facade_az: float = 0.0) -> object:
    """Diámetro del transportador perpendicular a la normal de fachada."""
    ends = rotate_points(np.array([WEST, EAST]), facade_az)
    (line,) = ax.plot(
        ends[:, 0],
        ends[:, 1],
        color=EW_LINE_COLOR,
        linewidth=EW_LINEWIDTH,
        zorder=PROTRACTOR_ZORDER - 0.1,
    )
    return line


def draw_ew_diameter(ax: Axes) -> object:
    """Compatibilidad: diámetro Este–Oeste (fachada Norte)."""
    return draw_facade_diameter(ax, facade_az=0.0)


def draw_protractor(
    ax: Axes,
    mask_alt: float | None,
    *,
    show_grid: bool = True,
    protractor_step: int = 10,
    facade_az: float = 0.0,
) -> None:
    """Orquestador del transportador SOL-AR."""
    if mask_alt is None:
        return

    draw_facade_diameter(ax, facade_az=facade_az)
    if show_grid:
        draw_protractor_grid(ax, step=protractor_step, facade_az=facade_az)
    draw_alpha_mask(ax, mask_alt, facade_az=facade_az)


def draw_vertical_fin_mask(
    ax: Axes,
    beta_deg: float,
    *,
    facade_az: float = 0.0,
    fill_color: str = FIN_FILL_COLOR,
    fill_alpha: float = FIN_FILL_ALPHA,
) -> list:
    """
    Máscara de aletas verticales: dos sectores laterales con |γ| ≥ β
    en el semicírculo frontal (horizonte r=1).
    """
    # En marco Norte: normal +y. Sectores frontales laterales:
    # izquierda: azimut chart desde (90-beta) hasta 90 respecto a N? 
    # Chart angles: 0=N, 90=E (matplotlib polar from +y via +x).
    # Wedge uses math angles from +x CCW. Convert carefully.
    # Simpler: polygon in local frame then rotate.
    patches = []
    for sign in (-1.0, 1.0):
        # Local (N-up): points on horizon from gamma=beta to gamma=90
        gammas = np.linspace(beta_deg, 90.0, 40)
        xs = np.sin(np.radians(sign * gammas))
        ys = np.cos(np.radians(sign * gammas))
        # close via origin (zenith) then back
        verts = np.column_stack([xs, ys])
        verts = np.vstack([[0.0, 0.0], verts, [0.0, 0.0]])
        verts = rotate_points(verts, facade_az)
        patch = PathPatch(
            Path(verts),
            facecolor=fill_color,
            edgecolor="none",
            alpha=fill_alpha,
            zorder=PROTRACTOR_ZORDER,
        )
        ax.add_patch(patch)
        patches.append(patch)

    # Cut-off rays at ±β
    for sign in (-1.0, 1.0):
        local = np.array([[0.0, 0.0], [np.sin(np.radians(sign * beta_deg)), np.cos(np.radians(sign * beta_deg))]])
        pts = rotate_points(local, facade_az)
        ax.plot(
            pts[:, 0],
            pts[:, 1],
            color=ACTIVE_LINE_COLOR,
            linewidth=ACTIVE_LINEWIDTH,
            zorder=PROTRACTOR_ZORDER + 0.1,
        )
    draw_facade_diameter(ax, facade_az=facade_az)
    return patches
