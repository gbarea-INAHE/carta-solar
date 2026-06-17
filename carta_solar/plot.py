from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from carta_solar.annotations import (
    draw_critical_months_highlight,
    draw_critical_overlays,
    draw_section_diagram,
)
from carta_solar.branding import add_figure_credit
from carta_solar.config import CartaSolarConfig
from carta_solar.format_utils import site_slug
from carta_solar.mask import draw_protractor
from carta_solar.solar import r_from_alt, solar_alt_az, xy_from_alt_az

REPRESENTATIVE_DAYS = {
    "21 Jun": 172,
    "21 Jul": 202,
    "21 Ago": 233,
    "21 Sep": 264,
    "21 Oct": 294,
    "21 Nov": 325,
    "21 Dic": 355,
    "21 Ene": 21,
    "21 Feb": 52,
    "21 Mar": 80,
    "21 Abr": 111,
    "21 May": 141,
}

BOTH_END_LABELS = {"21 Jun", "21 Sep", "21 Dic", "21 Mar"}
START_ONLY_LABELS = {"21 Jul", "21 Ago", "21 Oct", "21 Nov"}

Z_GRID = 1.0
Z_HOUR_LINES = 2.8
Z_TRAJECTORIES = 3.0
Z_LABEL = 10.0

CARDINAL_RADIUS = 1.20
MONTH_LABEL_OUTSET = 1.025

HOUR_LINE_COLOR = "#1D6FBF"
HOUR_LINE_STYLE = (0, (1.2, 2.4))
MONTH_LINE_COLOR = "#333333"
MONTH_LINE_WIDTH = 1.2
HOUR_LINE_WIDTH = 0.9

LABEL_BBOX = dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.88)


def _nudge_label_outward(x: float, y: float, *, outset: float = MONTH_LABEL_OUTSET) -> tuple[float, float]:
    """Desplaza levemente la etiqueta hacia afuera del punto de la trayectoria."""
    r = float(np.hypot(x, y))
    if r < 1e-9:
        return x, y
    scale = max(outset, 1.02) / r if r < 1.0 else outset
    return x * scale, y * scale


def _place_chart_label(
    ax: plt.Axes,
    x: float,
    y: float,
    text: str,
    *,
    fontsize: float = 9,
    ha: str = "center",
    va: str = "center",
) -> None:
    ax.text(
        x,
        y,
        text,
        fontsize=fontsize,
        ha=ha,
        va=va,
        color="black",
        zorder=Z_LABEL,
        bbox=LABEL_BBOX,
    )


def _place_month_label(
    ax: plt.Axes,
    x: float,
    y: float,
    text: str,
    *,
    fontsize: float = 9,
    ha: str = "center",
) -> None:
    lx, ly = _nudge_label_outward(x, y)
    _place_chart_label(ax, lx, ly, text, fontsize=fontsize, ha=ha, va="center")


def _draw_solar_chart(ax: plt.Axes, config: CartaSolarConfig) -> None:
    ax.set_aspect("equal")
    ax.axis("off")

    ax.add_patch(
        plt.Circle((0, 0), 1, fill=False, linewidth=1.5, zorder=Z_GRID)
    )

    altitude_labels: list[tuple[float, int]] = []
    for alt in range(10, 90, 10):
        r = r_from_alt(alt)
        ax.add_patch(
            plt.Circle(
                (0, 0),
                r,
                fill=False,
                linestyle="--",
                linewidth=0.6,
                alpha=0.6,
                zorder=Z_GRID,
            )
        )
        altitude_labels.append((r, alt))

    for az in range(0, 360, 15):
        x, y = xy_from_alt_az(0, az)
        ax.plot([0, x], [0, y], linestyle="--", linewidth=0.5, alpha=0.5, zorder=Z_GRID)

    if config.mask_alt is not None:
        draw_critical_months_highlight(ax, config)
        draw_protractor(
            ax,
            config.mask_alt,
            show_grid=config.show_protractor_grid,
            protractor_step=config.protractor_step,
        )

    hours = np.linspace(4, 20, 481)
    month_label_points: list[tuple[float, float, str, float, str]] = []
    for label, day in REPRESENTATIVE_DAYS.items():
        xs, ys = [], []
        for hour in hours:
            alt, az = solar_alt_az(config.lat, day, hour)
            if alt > 0:
                x, y = xy_from_alt_az(alt, az)
                xs.append(x)
                ys.append(y)
        ax.plot(xs, ys, linewidth=MONTH_LINE_WIDTH, color=MONTH_LINE_COLOR, zorder=Z_TRAJECTORIES)
        if xs:
            if label in BOTH_END_LABELS:
                month_label_points.append((xs[0], ys[0], label, 9, "center"))
                month_label_points.append((xs[-1], ys[-1], label, 9, "center"))
            elif label in START_ONLY_LABELS:
                month_label_points.append((xs[0], ys[0], label, 9, "center"))
            else:
                month_label_points.append((xs[-1], ys[-1], label, 9, "center"))

    hour_label_points: list[tuple[float, float, str]] = []
    for hour in range(config.hour_start, config.hour_end):
        xs, ys = [], []
        for day in range(1, 366, 2):
            alt, az = solar_alt_az(config.lat, day, hour)
            if alt > 0:
                x, y = xy_from_alt_az(alt, az)
                xs.append(x)
                ys.append(y)
        ax.plot(
            xs,
            ys,
            linewidth=HOUR_LINE_WIDTH,
            linestyle=HOUR_LINE_STYLE,
            color=HOUR_LINE_COLOR,
            alpha=0.9,
            zorder=Z_HOUR_LINES,
        )
        alt, az = solar_alt_az(config.lat, 80, hour)
        if alt > 0:
            x, y = xy_from_alt_az(alt, az)
            hour_label_points.append((x, y, str(hour)))

    draw_critical_overlays(ax, config)

    for r, alt in altitude_labels:
        ax.text(
            0.02,
            r,
            f"{alt}°",
            fontsize=8,
            va="bottom",
            ha="left",
            color="black",
            zorder=Z_LABEL,
        )

    for az in range(0, 360, 30):
        ax.text(
            1.08 * np.sin(np.radians(az)),
            1.08 * np.cos(np.radians(az)),
            f"{az}°",
            ha="center",
            va="center",
            fontsize=8,
            color="black",
            zorder=Z_LABEL,
        )

    for label, az in [("N", 0), ("E", 90), ("S", 180), ("O", 270)]:
        ax.text(
            CARDINAL_RADIUS * np.sin(np.radians(az)),
            CARDINAL_RADIUS * np.cos(np.radians(az)),
            label,
            ha="center",
            va="center",
            fontsize=16,
            fontweight="bold",
            zorder=Z_LABEL,
        )

    for x, y, label, fontsize, ha in month_label_points:
        _place_month_label(ax, x, y, label, fontsize=fontsize, ha=ha)

    for x, y, label in hour_label_points:
        _place_chart_label(ax, x, y, label, fontsize=9)

    ax.set_xlim(-1.30, 1.30)
    ax.set_ylim(-1.30, 1.30)
    ax.set_title("Carta solar", fontsize=11, pad=8)


def generate_carta_solar(config: CartaSolarConfig) -> plt.Figure:
    config.validate()

    fig = plt.figure(figsize=config.figsize, layout="constrained")
    gs = fig.add_gridspec(1, 2, width_ratios=[1.55, 0.85])
    ax_solar = fig.add_subplot(gs[0, 0])
    ax_section = fig.add_subplot(gs[0, 1])

    _draw_solar_chart(ax_solar, config)
    draw_section_diagram(ax_section, config)
    add_figure_credit(fig)

    return fig


def build_output_basename(config: CartaSolarConfig) -> str:
    slug = site_slug(config.site_name)
    if config.mask_alt is not None:
        return f"carta_solar_{slug}_mascara_{config.mask_alt:g}"
    return f"carta_solar_{slug}"


def save_carta_solar(
    fig: plt.Figure,
    config: CartaSolarConfig,
    *,
    png: bool = True,
    pdf: bool = True,
) -> dict[str, Path]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    basename = build_output_basename(config)
    saved: dict[str, Path] = {}

    if png:
        png_path = config.output_dir / f"{basename}.png"
        fig.savefig(png_path, dpi=config.dpi, bbox_inches="tight")
        saved["png"] = png_path

    if pdf:
        pdf_path = config.output_dir / f"{basename}.pdf"
        fig.savefig(pdf_path, bbox_inches="tight")
        saved["pdf"] = pdf_path

    return saved


def save_carta_solar_to_path(fig: plt.Figure, path: Path, *, dpi: int = 300) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".png":
        fig.savefig(path, dpi=dpi, bbox_inches="tight")
    else:
        fig.savefig(path, bbox_inches="tight")
    return path
