"""Cálculo constructivo de alero horizontal (fachada ecuatorial)."""

from __future__ import annotations

import math
from dataclasses import replace

from carta_solar.config import CartaSolarConfig
from carta_solar.critical import compute_required_alpha


def overhang_projection(effective_height_m: float, alpha_deg: float) -> float:
    """
    Profundidad horizontal del alero P (m).

    P = H_eff / tan(α), con α = mín. ángulo de perfil ε del período crítico.
    """
    if effective_height_m <= 0:
        raise ValueError("La altura efectiva debe ser mayor que 0.")
    if not 0 < alpha_deg < 90:
        raise ValueError("El ángulo α debe estar entre 0° y 90°.")
    return effective_height_m / math.tan(math.radians(alpha_deg))


def compute_overhang_from_config(config: CartaSolarConfig) -> tuple[float, float, int | None]:
    """
    Calcula α (mín ε) y profundidad P del alero.

    Retorna (alpha_deg, projection_m, limiting_month).
    """
    alpha, _samples, month = compute_required_alpha(
        config.lat,
        config.critical_months,
        config.critical_hour_start,
        config.critical_hour_end,
        facade_az=config.facade_azimuth,
    )
    if not 0 < alpha < 90:
        raise ValueError(
            "No se pudo determinar un α de diseño en (0°, 90°) para el período crítico."
        )
    projection = overhang_projection(config.effective_shading_height_m, alpha)
    return alpha, projection, month


def apply_computed_mask(config: CartaSolarConfig) -> CartaSolarConfig:
    """Devuelve una copia de config con mask_alt asignado automáticamente."""
    alpha, _, _ = compute_overhang_from_config(config)
    return replace(config, mask_alt=alpha)
