"""Análisis del período crítico y cálculo de α por ángulo de perfil ε."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from carta_solar.solar import (
    alt_az_from_xy,
    profile_angle,
    signed_bearing_diff,
    solar_alt_az,
    xy_from_alt_az,
)

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

DEFAULT_CRITICAL_MONTHS_HS: frozenset[int] = frozenset({11, 12, 1, 2, 3})
DEFAULT_CRITICAL_MONTHS_HN: frozenset[int] = frozenset({5, 6, 7, 8, 9})
DEFAULT_CRITICAL_MONTHS: frozenset[int] = DEFAULT_CRITICAL_MONTHS_HS

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


def default_critical_months_for_lat(lat: float) -> frozenset[int]:
    """Verano local: Nov–Mar (HS) o May–Sep (HN)."""
    return DEFAULT_CRITICAL_MONTHS_HS if lat < 0 else DEFAULT_CRITICAL_MONTHS_HN


def facade_azimuth_for_lat(lat: float) -> float:
    """Fachada ecuatorial: Norte (0°) en HS, Sur (180°) en HN."""
    return 0.0 if lat < 0 else 180.0


def facade_label_for_lat(lat: float) -> str:
    return "Norte" if lat < 0 else "Sur"


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


def is_in_equatorial_sector(az: float, y: float, facade_az: float = 0.0) -> bool:
    """Semicírculo hacia el ecuador (frente a la fachada ecuatorial)."""
    gamma = abs(signed_bearing_diff(az, facade_az))
    in_front = gamma <= 90.0 + 1e-9
    if facade_az % 360.0 == 0.0:
        return in_front and y >= -1e-9
    return in_front and y <= 1e-9


def is_in_northern_sector(az: float, y: float) -> bool:
    """Compatibilidad: sector norte (fachada Norte)."""
    return is_in_equatorial_sector(az, y, facade_az=0.0)


def max_y_on_alpha_arc(x: float, alpha: float) -> float:
    """Cota y del arco α (fachada Norte) para una abscisa x."""
    from carta_solar.mask import circle_params_for_alpha

    y_c, radius, _ = circle_params_for_alpha(alpha)
    if abs(x) > radius + 1e-9:
        return 0.0
    return float(y_c + np.sqrt(max(radius * radius - x * x, 0.0)))


def is_protected_by_alpha(
    alt: float,
    az: float,
    alpha: float,
    facade_az: float = 0.0,
) -> bool:
    """
    Protegido por alero de ángulo α ⇔ ε ≥ α (tol. 1e-6°).

    Sol detrás de la fachada se considera protegido.
    """
    eps = profile_angle(alt, az, facade_az)
    if eps is None:
        return True
    return eps + 1e-6 >= alpha


def is_point_shaded_by_alpha(
    x: float,
    y: float,
    alpha: float,
    facade_az: float = 0.0,
) -> bool:
    """True si el Sol en (x, y) queda protegido por el alero α."""
    alt, az = alt_az_from_xy(x, y)
    if alt <= 0:
        return False
    return is_protected_by_alpha(alt, az, alpha, facade_az)


def required_alpha_for_point(
    alt: float,
    az: float,
    facade_az: float = 0.0,
) -> float | None:
    """ε requerido para proteger el punto (None si está detrás de la fachada)."""
    return profile_angle(alt, az, facade_az)


def min_alpha_for_point(x: float, y: float, facade_az: float = 0.0) -> float:
    """ε en grados para el punto (x, y); 0 si está detrás o bajo el horizonte."""
    alt, az = alt_az_from_xy(x, y)
    eps = profile_angle(alt, az, facade_az)
    if eps is None:
        return 0.0
    return eps


def collect_critical_samples(
    lat: float,
    months: frozenset[int],
    hour_start: int,
    hour_end: int,
    *,
    hour_step: float = 0.5,
    facade_az: float | None = None,
) -> list[SolarSample]:
    """Muestrea posiciones solares del período crítico frente a la fachada."""
    if facade_az is None:
        facade_az = facade_azimuth_for_lat(lat)
    samples: list[SolarSample] = []
    hours = np.arange(hour_start, hour_end + 1e-9, hour_step)

    for month in sorted(months):
        day = MONTH_TO_DAY_OF_YEAR[month]
        for hour in hours:
            alt, az = solar_alt_az(lat, day, float(hour))
            if alt <= 0:
                continue
            x, y = xy_from_alt_az(alt, az)
            if not is_in_equatorial_sector(az, y, facade_az):
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
    Altitud solar mínima al mediodía (12 h) entre los meses críticos.

    Referencia/diagnóstico; el dimensionamiento usa `compute_required_alpha`.
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


def compute_required_alpha(
    lat: float,
    months: frozenset[int],
    hour_start: int,
    hour_end: int,
    *,
    facade_az: float | None = None,
) -> tuple[float, list[SolarSample], int | None]:
    """
    α de diseño: mínimo ángulo de perfil ε sobre las muestras del período crítico.

    Retorna (alpha_deg, samples, limiting_month). Si no hay muestras, α = 90°.
    """
    if facade_az is None:
        facade_az = facade_azimuth_for_lat(lat)
    samples = collect_critical_samples(
        lat, months, hour_start, hour_end, facade_az=facade_az
    )
    if not samples:
        return 90.0, [], None

    best_eps = float("inf")
    limiting_month: int | None = None
    for sample in samples:
        eps = profile_angle(sample.alt, sample.az, facade_az)
        if eps is None:
            continue
        if eps < best_eps:
            best_eps = eps
            limiting_month = sample.month

    if best_eps == float("inf"):
        return 90.0, samples, None
    return best_eps, samples, limiting_month


def compute_minimum_alpha(
    lat: float,
    months: frozenset[int],
    hour_start: int,
    hour_end: int,
) -> tuple[float, list[SolarSample]]:
    """Alias histórico de `compute_required_alpha` (sin mes limitante)."""
    alpha, samples, _ = compute_required_alpha(lat, months, hour_start, hour_end)
    return alpha, samples


def find_unprotected_samples(
    samples: list[SolarSample],
    alpha: float | None,
    *,
    facade_az: float = 0.0,
) -> list[SolarSample]:
    """Puntos del período crítico no cubiertos por la máscara α."""
    if alpha is None:
        return list(samples)
    return [
        s
        for s in samples
        if not is_protected_by_alpha(s.alt, s.az, alpha, facade_az)
    ]


def format_exposure_report(
    samples: list[SolarSample],
    alpha: float | None,
    *,
    max_lines: int = 8,
    limiting_month: int | None = None,
    noon_month: int | None = None,
    facade_az: float = 0.0,
) -> str:
    """Texto resumen de cobertura y huecos."""
    month = limiting_month if limiting_month is not None else noon_month

    if alpha is None:
        if not samples:
            return "Sin muestras en el período crítico (sector ecuatorial)."
        return (
            f"Período crítico: {len(samples)} posiciones frente a la fachada "
            "(sin máscara)."
        )

    alpha_note = ""
    if month is not None:
        alpha_note = (
            f"α = {alpha:g}° (mín. ángulo de perfil ε del período crítico, "
            f"mes {MONTH_NAMES[month]}).\n"
        )
    else:
        alpha_note = (
            f"α = {alpha:g}° (mín. ángulo de perfil ε del período crítico).\n"
        )

    if not samples:
        return alpha_note + "Sin muestras horarias frente a la fachada."

    unprotected = find_unprotected_samples(samples, alpha, facade_az=facade_az)
    total = len(samples)
    covered = total - len(unprotected)
    pct = 100.0 * covered / total
    header = (
        f"{alpha_note}"
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
