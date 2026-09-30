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
    design_short_fins,
    design_short_fins_from_config,
    format_architect_fin_report,
    suggested_critical_hours,
)

__all__ = [
    "apply_overhang_design",
    "compute_overhang_design",
    "overhang_projection",
    "apply_vertical_fin_design",
    "compute_vertical_fin_design",
    "describe_fin_design",
    "design_short_fins",
    "design_short_fins_from_config",
    "format_architect_fin_report",
    "suggested_critical_hours",
]
