"""Parasol vertical — dimensión por ángulo de sombra horizontal φ."""

from __future__ import annotations

import math
from dataclasses import replace

from carta_solar.config import CartaSolarConfig
from carta_solar.critical import (
    collect_critical_samples,
    facade_azimuth_for_lat,
)
from carta_solar.solar import signed_bearing_diff


def horizontal_shadow_angle(
    az: float,
    facade_az: float = 0.0,
) -> float | None:
    """
    Ángulo horizontal φ (°) entre la proyección del sol y la normal de fachada.

    φ = |γ|; None si el sol está detrás de la fachada (|γ| > 90°).
    """
    gamma = abs(signed_bearing_diff(az, facade_az))
    if gamma > 90.0 + 1e-9:
        return None
    return gamma


def is_protected_by_fin_angle(
    az: float,
    beta_deg: float,
    facade_az: float = 0.0,
) -> bool:
    """
    Protegido por aletas de ángulo de corte β ⇔ |γ| ≥ β (o detrás de fachada).

    β pequeño ⇒ alerón más profundo ⇒ más protección.
    """
    phi = horizontal_shadow_angle(az, facade_az)
    if phi is None:
        return True
    return phi + 1e-6 >= beta_deg


def fin_depth_from_angle(
    window_width_m: float,
    beta_deg: float,
    *,
    bilateral: bool = True,
) -> float:
    """
    Profundidad D (m) de aleta vertical.

    Bilateral: D = (W/2) / tan(β); unilateral: D = W / tan(β).
    """
    if window_width_m <= 0:
        raise ValueError("El ancho de ventana debe ser mayor que 0.")
    if not 0 < beta_deg < 90:
        raise ValueError("El ángulo β debe estar entre 0° y 90°.")
    half = window_width_m / 2.0 if bilateral else window_width_m
    return half / math.tan(math.radians(beta_deg))


def compute_required_fin_angle(
    lat: float,
    months: frozenset[int],
    hour_start: int,
    hour_end: int,
    *,
    facade_az: float | None = None,
    lon: float = 0.0,
    use_civil_hours: bool = False,
    timezone_utc_hours: float | None = None,
    min_gamma_deg: float = 8.0,
) -> tuple[float, list, int | None]:
    """
    β de diseño = mín |γ| entre muestras frontales con |γ| ≥ min_gamma_deg.

    Muestras casi normales (γ≈0) no se pueden sombrear solo con aletas verticales;
    se excluyen por debajo de min_gamma_deg. Retorna (beta, samples, month).
    """
    if facade_az is None:
        facade_az = facade_azimuth_for_lat(lat)
    samples = collect_critical_samples(
        lat,
        months,
        hour_start,
        hour_end,
        facade_az=facade_az,
        lon=lon,
        use_civil_hours=use_civil_hours,
        timezone_utc_hours=timezone_utc_hours,
    )
    if not samples:
        return 90.0, [], None

    best = float("inf")
    limiting_month: int | None = None
    usable = 0
    for s in samples:
        phi = horizontal_shadow_angle(s.az, facade_az)
        if phi is None or phi < min_gamma_deg:
            continue
        usable += 1
        if phi < best:
            best = phi
            limiting_month = s.month

    if usable == 0:
        return 90.0, samples, None
    return best, samples, limiting_month


def compute_vertical_fin_design(
    config: CartaSolarConfig,
) -> tuple[float, float, int | None]:
    """Retorna (beta_deg, depth_m, limiting_month)."""
    beta, _samples, month = compute_required_fin_angle(
        config.lat,
        config.critical_months,
        config.critical_hour_start,
        config.critical_hour_end,
        facade_az=config.facade_azimuth,
        lon=config.lon,
        use_civil_hours=config.use_civil_hours,
        timezone_utc_hours=config.timezone_utc_offset,
    )
    if not 0 < beta < 90:
        raise ValueError(
            "No hay muestras con |γ| suficiente para dimensionar aletas verticales. "
            "Probá horas de mañana (Este) o tarde (Oeste), o combiná con alero."
        )
    bilateral = config.fin_arrangement != "single"
    depth = fin_depth_from_angle(
        config.window_width_m, beta, bilateral=bilateral
    )
    return beta, depth, month


def apply_vertical_fin_design(config: CartaSolarConfig) -> CartaSolarConfig:
    """Copia con mask_fin_angle = β (mask_alt queda None)."""
    beta, _, _ = compute_vertical_fin_design(config)
    return replace(config, mask_fin_angle=beta, mask_alt=None)


def find_unprotected_by_fin(
    samples: list,
    beta: float | None,
    facade_az: float,
) -> list:
    if beta is None:
        return list(samples)
    return [
        s
        for s in samples
        if not is_protected_by_fin_angle(s.az, beta, facade_az)
    ]
