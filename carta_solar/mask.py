"""Transportador de máscara estilo SOL-AR (arcos circulares anclados en Este/Oeste).

Geometría del transportador en carta estereográfica
---------------------------------------------------
Cada curva de ángulo α NO es un círculo de altitud ni alt = α×cos(δ).
Es un arco de circunferencia en el plano de proyección que:

  1. Pasa por Oeste (-1, 0) y Este (1, 0) en el horizonte.
  2. Corta el meridiano de la fachada ecuatorial en (0, ±r(α)),
     con r(α) = tan((90°-α)/2). Para fachada Sur se refleja por el
     diámetro E–O (y → −y).

Así las curvas α=10°, 20°, … coinciden en el eje de fachada con la grilla de
altitud (equidistantes en grados) y no se deforman al acercarse al cenit.
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
EW_LINE_COLOR = "#000000"
EW_LINEWIDTH = 1.0

PROTRACTOR_ZORDER = 2.5
CURVE_SAMPLE_POINTS = 120

WEST = (-1.0, 0.0)
EAST = (1.0, 0.0)


def _y_sign(facade_az: float) -> float:
    """+1 fachada Norte, −1 fachada Sur."""
    return -1.0 if (facade_az % 360.0) == 180.0 else 1.0


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
    """Arco del transportador O → pico ecuatorial → E (reflejado si fachada Sur)."""
    y_c, radius, _ = circle_params_for_alpha(alpha)

    theta_w = float(np.arctan2(-y_c, -1.0))
    theta_e = float(np.arctan2(-y_c, 1.0))

    thetas = np.linspace(theta_w, theta_e, num_points)
    x = radius * np.cos(thetas)
    y = (y_c + radius * np.sin(thetas)) * _y_sign(facade_az)
    return np.column_stack([x, y])


def build_shaded_region_vertices(
    alpha: float,
    *,
    num_points: int = CURVE_SAMPLE_POINTS,
    facade_az: float = 0.0,
) -> np.ndarray:
    """Polígono cerrado: arco α + diámetro horizontal E → O (y = 0)."""
    curve = alpha_curve_points(alpha, num_points=num_points, facade_az=facade_az)
    diameter = np.array([EAST, WEST])
    return np.vstack([curve, diameter])


def north_peak_y(alpha: float) -> float:
    """Cota y donde el arco α corta el meridiano Norte (fachada Norte)."""
    _, _, h = circle_params_for_alpha(alpha)
    return h


def facade_peak_xy(alpha: float, facade_az: float = 0.0) -> tuple[float, float]:
    """Punto donde el arco α corta el meridiano de la fachada."""
    h = north_peak_y(alpha)
    return 0.0, h * _y_sign(facade_az)


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


def draw_ew_diameter(ax: Axes) -> object:
    """Diámetro horizontal Este–Oeste."""
    (line,) = ax.plot(
        [-1, 1],
        [0, 0],
        color=EW_LINE_COLOR,
        linewidth=EW_LINEWIDTH,
        zorder=PROTRACTOR_ZORDER - 0.1,
    )
    return line


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

    draw_ew_diameter(ax)
    if show_grid:
        draw_protractor_grid(ax, step=protractor_step, facade_az=facade_az)
    draw_alpha_mask(ax, mask_alt, facade_az=facade_az)
