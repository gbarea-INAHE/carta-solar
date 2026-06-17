"""Análisis del período crítico y cálculo de α mínimo de protección."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from matplotlib.path import Path

from carta_solar.mask import build_shaded_region_vertices
from carta_solar.solar import solar_alt_az, xy_from_alt_az

# Día representativo (21) de cada mes en día del año.
MONTH_TO_DAY_OF_YEAR: dict[int, int] = {
    1: 21,
    2: 52,
    3: 80,
    4: 111,
    5: 141,
    6: 172,
    7: 202,
    8: 233,
    9: 264,
    10: 294,
    11: 325,
    12: 355,
}

DEFAULT_CRITICAL_MONTHS: frozenset[int] = frozenset({11, 12, 1, 2, 3})

MONTH_NAMES = {
    1: "Ene",
    2: "Feb",
    3: "Mar",
    4: "Abr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Ago",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dic",
}


@dataclass(frozen=True)
class SolarSample:
    month: int
    day_of_year: int
    hour: float
    alt: float
    az: float
    x: float
    y: float

    @property
    def month_label(self) -> str:
        return MONTH_NAMES[self.month]

    def label(self) -> str:
        h = int(self.hour)
        m = int(round((self.hour - h) * 60))
        return f"{self.month_label} {h:02d}:{m:02d}h (alt {self.alt:.1f}°)"


def is_in_northern_sector(az: float, y: float) -> bool:
    """Semicírculo superior de la carta (sector norte para alero)."""
    az_norm = az % 360.0
    in_az_range = az_norm >= 270.0 or az_norm <= 90.0
    return in_az_range and y >= 0.0


def max_y_on_alpha_arc(x: float, alpha: float) -> float:
    """Cota y máxima del arco α para una abscisa x (borde superior de la zona sombreada)."""
    from carta_solar.mask import circle_params_for_alpha

    y_c, radius, _ = circle_params_for_alpha(alpha)
    if abs(x) > radius + 1e-9:
        return 0.0
    return float(y_c + np.sqrt(max(radius * radius - x * x, 0.0)))


def is_point_shaded_by_alpha(x: float, y: float, alpha: float) -> bool:
    """
    True si el Sol en (x, y) queda en la zona protegida (bajo el arco α, hacia el horizonte).

    En la carta, y mayor = más cerca del horizonte = menor altitud solar.
    """
    if y < -1e-9:
        return False
    threshold = max_y_on_alpha_arc(x, alpha)
    return y >= threshold - 1e-6


def min_alpha_for_point(x: float, y: float, *, precision: float = 0.25) -> float:
    """Menor α (°) que aún protege el punto (alero más shallow posible)."""
    if y < 0:
        return 0.0

    lo, hi = 0.5, 89.0
    if not is_point_shaded_by_alpha(x, y, hi):
        return hi

    while hi - lo > precision:
        mid = (lo + hi) / 2.0
        if is_point_shaded_by_alpha(x, y, mid):
            hi = mid
        else:
            lo = mid
    return hi


def collect_critical_samples(
    lat: float,
    months: frozenset[int],
    hour_start: int,
    hour_end: int,
    *,
    hour_step: float = 0.5,
) -> list[SolarSample]:
    """Muestrea posiciones solares del período crítico en el sector norte."""
    samples: list[SolarSample] = []
    hours = np.arange(hour_start, hour_end + 1e-9, hour_step)

    for month in sorted(months):
        day = MONTH_TO_DAY_OF_YEAR[month]
        for hour in hours:
            alt, az = solar_alt_az(lat, day, float(hour))
            if alt <= 0:
                continue
            x, y = xy_from_alt_az(alt, az)
            if not is_in_northern_sector(az, y):
                continue
            samples.append(
                SolarSample(
                    month=month,
                    day_of_year=day,
                    hour=float(hour),
                    alt=alt,
                    az=az,
                    x=x,
                    y=y,
                )
            )
    return samples


def compute_noon_alpha(
    lat: float,
    months: frozenset[int],
) -> tuple[float, int]:
    """
    α de dimensionamiento: altitud solar mínima al mediodía (12 h) en el
    meridiano Norte, entre los meses críticos seleccionados.

    En la carta estereográfica coincide con el círculo de altitud en el eje N.
    Retorna (alpha_deg, month_with_min_alt).
    """
    if not months:
        raise ValueError("Seleccioná al menos un mes del período crítico.")

    candidates: list[tuple[float, int]] = []
    for month in months:
        day = MONTH_TO_DAY_OF_YEAR[month]
        alt, _az = solar_alt_az(lat, day, 12.0)
        if alt > 0:
            candidates.append((alt, month))

    if not candidates:
        raise ValueError(
            "Ningún mes crítico tiene sol sobre el horizonte al mediodía solar."
        )

    min_alt, month = min(candidates, key=lambda item: item[0])
    return min_alt, month


def compute_minimum_alpha(
    lat: float,
    months: frozenset[int],
    hour_start: int,
    hour_end: int,
) -> tuple[float, list[SolarSample]]:
    """
    α mínimo que cubre todos los puntos del período crítico en sector norte.

    Retorna (alpha_min, samples).
    """
    samples = collect_critical_samples(lat, months, hour_start, hour_end)
    if not samples:
        return 0.0, []

    required = [min_alpha_for_point(s.x, s.y) for s in samples]
    return max(required), samples


def find_unprotected_samples(
    samples: list[SolarSample],
    alpha: float | None,
) -> list[SolarSample]:
    """Puntos del período crítico no cubiertos por la máscara α."""
    if alpha is None:
        return list(samples)
    return [s for s in samples if not is_point_shaded_by_alpha(s.x, s.y, alpha)]


def format_exposure_report(
    samples: list[SolarSample],
    alpha: float | None,
    *,
    max_lines: int = 8,
    noon_month: int | None = None,
) -> str:
    """Texto resumen de cobertura y huecos."""
    if alpha is None:
        if not samples:
            return "Sin muestras en el período crítico (sector norte)."
        return f"Período crítico: {len(samples)} posiciones en sector norte (sin máscara)."

    noon_note = ""
    if noon_month is not None:
        noon_note = (
            f"α = {alpha:g}° (altitud al mediodía solar, mes {MONTH_NAMES[noon_month]}).\n"
        )

    if not samples:
        return noon_note + "Sin muestras horarias en el sector norte."

    unprotected = find_unprotected_samples(samples, alpha)
    total = len(samples)
    covered = total - len(unprotected)
    pct = 100.0 * covered / total
    header = (
        f"{noon_note}"
        f"Rango horario {total} posiciones: {covered}/{total} bajo máscara ({pct:.0f}%)."
    )

    if not unprotected:
        return header + "\nPeríodo horario completamente cubierto."

    lines = [header, "Posiciones fuera de máscara (sol expuesto):"]
    for sample in unprotected[:max_lines]:
        lines.append(f"  • {sample.label()}")
    if len(unprotected) > max_lines:
        lines.append(f"  … y {len(unprotected) - max_lines} más")
    return "\n".join(lines)
