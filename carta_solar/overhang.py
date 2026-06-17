"""Cálculo constructivo de alero horizontal (fachada norte)."""

from __future__ import annotations

import math

from carta_solar.config import CartaSolarConfig
from carta_solar.critical import compute_noon_alpha


def overhang_projection(effective_height_m: float, alpha_deg: float) -> float:
    """
    Profundidad horizontal del alero P (m).

    P = H_eff / tan(α), con α = altitud solar al mediodía en el meridiano Norte.
    """
    if effective_height_m <= 0:
        raise ValueError("La altura efectiva debe ser mayor que 0.")
    if not 0 < alpha_deg < 90:
        raise ValueError("El ángulo α debe estar entre 0° y 90°.")
    return effective_height_m / math.tan(math.radians(alpha_deg))


def compute_overhang_from_config(config: CartaSolarConfig) -> tuple[float, float, int]:
    """
    Calcula α al mediodía solar y profundidad P del alero.

    Retorna (alpha_deg, projection_m, limiting_month).
    """
    alpha, month = compute_noon_alpha(config.lat, config.critical_months)
    projection = overhang_projection(config.effective_shading_height_m, alpha)
    return alpha, projection, month


def apply_computed_mask(config: CartaSolarConfig) -> CartaSolarConfig:
    """Devuelve una copia de config con mask_alt asignado automáticamente."""
    alpha, _, _ = compute_overhang_from_config(config)
    return CartaSolarConfig(
        site_name=config.site_name,
        lat=config.lat,
        lon=config.lon,
        mask_alt=alpha,
        show_protractor_grid=config.show_protractor_grid,
        protractor_step=config.protractor_step,
        hour_start=config.hour_start,
        hour_end=config.hour_end,
        output_dir=config.output_dir,
        dpi=config.dpi,
        figsize=config.figsize,
        sill_height_m=config.sill_height_m,
        window_height_m=config.window_height_m,
        gap_to_overhang_m=config.gap_to_overhang_m,
        critical_months=config.critical_months,
        critical_hour_start=config.critical_hour_start,
        critical_hour_end=config.critical_hour_end,
        highlight_critical_period=config.highlight_critical_period,
    )
