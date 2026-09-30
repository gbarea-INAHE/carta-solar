"""Parasol vertical — dimensión por ángulo de sombra horizontal φ (estilo SOL-AR)."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

import numpy as np

from carta_solar.config import CartaSolarConfig
from carta_solar.critical import (
    collect_critical_samples,
    facade_azimuth_for_lat,
)
from carta_solar.solar import signed_bearing_diff

# Percentil de |γ| para β automático (P25 ≈ cubrir el 75 % más oblicuo).
DEFAULT_BETA_PERCENTILE = 25.0
# Sol casi normal: no sombreable solo con aletas (aviso / exclusión del percentil).
NEAR_NORMAL_DEG = 15.0
# Profundidad máxima constructiva (bilateral): limita β mínimo.
DEFAULT_MAX_DEPTH_M = 2.5


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


def signed_horizontal_gamma(az: float, facade_az: float = 0.0) -> float | None:
    """γ con signo (izq − / der +); None si detrás de fachada."""
    gamma = signed_bearing_diff(az, facade_az)
    if abs(gamma) > 90.0 + 1e-9:
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


def min_beta_for_max_depth(
    window_width_m: float,
    max_depth_m: float,
    *,
    bilateral: bool = True,
) -> float:
    """β mínimo (°) para no superar max_depth_m."""
    if max_depth_m <= 0:
        raise ValueError("La profundidad máxima debe ser mayor que 0.")
    half = window_width_m / 2.0 if bilateral else window_width_m
    return math.degrees(math.atan(half / max_depth_m))


def suggested_critical_hours(facade_az: float) -> tuple[int, int]:
    """Horas críticas sugeridas según orientación (E mañana / O tarde)."""
    az = facade_az % 360.0
    dist_e = min(abs(az - 90.0), 360.0 - abs(az - 90.0))
    dist_w = min(abs(az - 270.0), 360.0 - abs(az - 270.0))
    if dist_e <= 45.0:
        return 7, 12
    if dist_w <= 45.0:
        return 12, 18
    return 10, 18


@dataclass(frozen=True)
class FinAngleResult:
    """Resultado del dimensionamiento automático de aletas (paridad SOL-AR)."""

    beta_deg: float
    samples: list
    limiting_month: int | None
    n_frontal: int
    n_near_normal: int
    coverage_frac: float
    percentile: float
    beta_left_deg: float | None = None
    beta_right_deg: float | None = None
    capped_by_max_depth: bool = False


def _percentile_phi(phis: list[float], percentile: float) -> float:
    if not phis:
        return 90.0
    return float(np.percentile(np.asarray(phis, dtype=float), percentile))


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
    percentile: float = DEFAULT_BETA_PERCENTILE,
    near_normal_deg: float = NEAR_NORMAL_DEG,
    min_beta_deg: float | None = None,
) -> FinAngleResult:
    """
    β de diseño por percentil de |γ| (estilo SOL-AR: no forzar mín |γ|).

    - Toma muestras frontales del período crítico.
    - Excluye sol casi normal (|γ| < near_normal_deg) del percentil (no sombreable
      solo con aletas) pero las cuenta en ``n_near_normal``.
    - β = percentil(φ usable); opcionalmente se eleva a ``min_beta_deg`` (tope de D).
    - También calcula β izq/der (signo de γ) para informe.
    """
    if facade_az is None:
        facade_az = facade_azimuth_for_lat(lat)
    if not 0.0 <= percentile <= 100.0:
        raise ValueError("El percentil debe estar entre 0 y 100.")

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
        return FinAngleResult(
            beta_deg=90.0,
            samples=[],
            limiting_month=None,
            n_frontal=0,
            n_near_normal=0,
            coverage_frac=1.0,
            percentile=percentile,
        )

    frontal_phi: list[float] = []
    left_phi: list[float] = []
    right_phi: list[float] = []
    usable_phi: list[float] = []
    n_near = 0
    limiting_month: int | None = None
    limiting_phi = float("inf")

    for s in samples:
        gamma = signed_horizontal_gamma(s.az, facade_az)
        if gamma is None:
            continue
        phi = abs(gamma)
        frontal_phi.append(phi)
        if gamma < 0:
            left_phi.append(phi)
        elif gamma > 0:
            right_phi.append(phi)
        if phi < near_normal_deg:
            n_near += 1
            continue
        usable_phi.append(phi)
        if phi < limiting_phi:
            limiting_phi = phi
            limiting_month = s.month

    n_frontal = len(frontal_phi)
    if n_frontal == 0:
        return FinAngleResult(
            beta_deg=90.0,
            samples=samples,
            limiting_month=None,
            n_frontal=0,
            n_near_normal=0,
            coverage_frac=1.0,
            percentile=percentile,
        )

    source = usable_phi if usable_phi else frontal_phi
    beta = _percentile_phi(source, percentile)
    capped = False
    if min_beta_deg is not None and beta < min_beta_deg:
        beta = float(min_beta_deg)
        capped = True

    # Clamp constructivo
    beta = min(max(beta, 1e-3), 89.999)

    covered = sum(1 for phi in frontal_phi if phi + 1e-6 >= beta)
    coverage = covered / n_frontal if n_frontal else 1.0

    beta_left = _percentile_phi(left_phi, percentile) if left_phi else None
    beta_right = _percentile_phi(right_phi, percentile) if right_phi else None

    return FinAngleResult(
        beta_deg=beta,
        samples=samples,
        limiting_month=limiting_month if usable_phi else None,
        n_frontal=n_frontal,
        n_near_normal=n_near,
        coverage_frac=coverage,
        percentile=percentile,
        beta_left_deg=beta_left,
        beta_right_deg=beta_right,
        capped_by_max_depth=capped,
    )


def compute_vertical_fin_design(
    config: CartaSolarConfig,
    *,
    percentile: float = DEFAULT_BETA_PERCENTILE,
    max_depth_m: float = DEFAULT_MAX_DEPTH_M,
) -> tuple[float, float, int | None]:
    """Retorna (beta_deg, depth_m, limiting_month)."""
    bilateral = config.fin_arrangement != "single"
    min_beta = min_beta_for_max_depth(
        config.window_width_m, max_depth_m, bilateral=bilateral
    )
    result = compute_required_fin_angle(
        config.lat,
        config.critical_months,
        config.critical_hour_start,
        config.critical_hour_end,
        facade_az=config.facade_azimuth,
        lon=config.lon,
        use_civil_hours=config.use_civil_hours,
        timezone_utc_hours=config.timezone_utc_offset,
        percentile=percentile,
        min_beta_deg=min_beta,
    )
    beta = result.beta_deg
    if not 0 < beta < 90 or result.n_frontal == 0:
        raise ValueError(
            "No hay muestras frontales para dimensionar aletas verticales. "
            "Probá horas de mañana (Este) o tarde (Oeste), o combiná con alero."
        )
    depth = fin_depth_from_angle(
        config.window_width_m, beta, bilateral=bilateral
    )
    return beta, depth, result.limiting_month


def describe_fin_design(
    config: CartaSolarConfig,
    *,
    percentile: float = DEFAULT_BETA_PERCENTILE,
    max_depth_m: float = DEFAULT_MAX_DEPTH_M,
) -> FinAngleResult:
    """Dimensionamiento con estadísticas (informe UI)."""
    bilateral = config.fin_arrangement != "single"
    min_beta = min_beta_for_max_depth(
        config.window_width_m, max_depth_m, bilateral=bilateral
    )
    return compute_required_fin_angle(
        config.lat,
        config.critical_months,
        config.critical_hour_start,
        config.critical_hour_end,
        facade_az=config.facade_azimuth,
        lon=config.lon,
        use_civil_hours=config.use_civil_hours,
        timezone_utc_hours=config.timezone_utc_offset,
        percentile=percentile,
        min_beta_deg=min_beta,
    )


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
