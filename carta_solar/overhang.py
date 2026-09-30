"""Cálculo constructivo de alero horizontal (API estable)."""

from __future__ import annotations

from carta_solar.config import DEVICE_OVERHANG, DEVICE_VERTICAL_FIN, CartaSolarConfig
from carta_solar.devices.overhang import (
    apply_overhang_design,
    compute_overhang_design,
    overhang_projection,
)
from carta_solar.devices.vertical_fin import apply_vertical_fin_design

__all__ = [
    "overhang_projection",
    "compute_overhang_from_config",
    "apply_computed_mask",
    "apply_computed_design",
]


def compute_overhang_from_config(config: CartaSolarConfig) -> tuple[float, float, int | None]:
    """Calcula α (mín ε) y profundidad P del alero."""
    return compute_overhang_design(config)


def apply_computed_mask(config: CartaSolarConfig) -> CartaSolarConfig:
    """Aplica el diseño del dispositivo activo (alero o aletas)."""
    if config.device_mode == DEVICE_VERTICAL_FIN:
        return apply_vertical_fin_design(config)
    if config.device_mode == DEVICE_OVERHANG:
        return apply_overhang_design(config)
    raise ValueError(f"Modo de dispositivo desconocido: {config.device_mode}")


def apply_computed_design(config: CartaSolarConfig) -> CartaSolarConfig:
    """Alias explícito de apply_computed_mask."""
    return apply_computed_mask(config)
