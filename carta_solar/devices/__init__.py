"""Dispositivos de sombreado: alero horizontal y parasol vertical."""

from carta_solar.devices.overhang import (
    apply_overhang_design,
    compute_overhang_design,
    overhang_projection,
)
from carta_solar.devices.vertical_fin import (
    apply_vertical_fin_design,
    compute_vertical_fin_design,
    describe_fin_design,
    suggested_critical_hours,
)

__all__ = [
    "apply_overhang_design",
    "compute_overhang_design",
    "overhang_projection",
    "apply_vertical_fin_design",
    "compute_vertical_fin_design",
    "describe_fin_design",
    "suggested_critical_hours",
]
