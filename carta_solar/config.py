"""Configuración de Carta Solar (sin imports pesados a nivel de módulo)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

SITE_NAME_MAX_LEN = 80
DEVICE_OVERHANG = "overhang"
DEVICE_VERTICAL_FIN = "vertical_fin"
DEVICE_MODES = frozenset({DEVICE_OVERHANG, DEVICE_VERTICAL_FIN})

# Verano HS por defecto; evita importar critical/numpy al cargar este módulo.
_DEFAULT_CRITICAL_MONTHS = frozenset({11, 12, 1, 2, 3})


@dataclass
class CartaSolarConfig:
    site_name: str = "Ñacuñán"
    lat: float = -34.0333
    lon: float = -67.9167
    mask_alt: float | None = None
    mask_fin_angle: float | None = None
    show_protractor_grid: bool = True
    protractor_step: int = 10
    hour_start: int = 5
    hour_end: int = 19
    output_dir: Path = Path("salida")
    dpi: int = 300
    figsize: tuple[float, float] = (16.0, 8.0)
    sill_height_m: float = 0.9
    window_height_m: float = 1.2
    gap_to_overhang_m: float = 0.3
    window_width_m: float = 1.5
    critical_months: frozenset[int] = field(
        default_factory=lambda: frozenset(_DEFAULT_CRITICAL_MONTHS)
    )
    critical_hour_start: int = 10
    critical_hour_end: int = 18
    highlight_critical_period: bool = True
    use_civil_hours: bool = False
    timezone_utc_offset: float | None = None
    # None → default por lat (fachada ecuatorial).
    facade_azimuth_override: float | None = None
    device_mode: str = DEVICE_OVERHANG
    # bilateral | single
    fin_arrangement: str = "bilateral"
    # full (export) | preview (UI rápida)
    chart_detail: str = "full"

    def __post_init__(self) -> None:
        self.output_dir = Path(self.output_dir)
        self.critical_months = frozenset(self.critical_months)
        self.site_name = self.site_name.strip()
        if len(self.site_name) > SITE_NAME_MAX_LEN:
            self.site_name = self.site_name[:SITE_NAME_MAX_LEN]
        self.device_mode = str(self.device_mode).strip().lower()
        self.fin_arrangement = str(self.fin_arrangement).strip().lower()
        self.chart_detail = str(self.chart_detail).strip().lower()
        if self.facade_azimuth_override is not None:
            self.facade_azimuth_override = float(self.facade_azimuth_override) % 360.0
        self.validate()

    @property
    def facade_azimuth(self) -> float:
        if self.facade_azimuth_override is not None:
            return self.facade_azimuth_override
        from carta_solar.critical import facade_azimuth_for_lat

        return facade_azimuth_for_lat(self.lat)

    @property
    def facade_label(self) -> str:
        from carta_solar.critical import facade_label_for_azimuth

        return facade_label_for_azimuth(self.facade_azimuth)

    @property
    def resolved_timezone_utc(self) -> float:
        if self.timezone_utc_offset is not None:
            return float(self.timezone_utc_offset)
        from carta_solar.solar import estimate_timezone_utc

        return estimate_timezone_utc(self.lon)

    @property
    def effective_shading_height_m(self) -> float:
        """Altura desde dintel inferior de ventana hasta el alero (h_v + h_g)."""
        return self.window_height_m + self.gap_to_overhang_m

    @property
    def total_wall_height_m(self) -> float:
        return self.sill_height_m + self.window_height_m + self.gap_to_overhang_m

    @property
    def is_preview(self) -> bool:
        return self.chart_detail == "preview"

    def validate(self) -> None:
        if not self.site_name:
            raise ValueError("El nombre del sitio no puede estar vacío.")
        if not -90 <= self.lat <= 90:
            raise ValueError("La latitud debe estar entre -90° y 90°.")
        if not -180 <= self.lon <= 180:
            raise ValueError("La longitud debe estar entre -180° y 180°.")
        if self.mask_alt is not None and not 0 < self.mask_alt < 90:
            raise ValueError("El ángulo α calculado debe estar entre 0° y 90°.")
        if self.mask_fin_angle is not None and not 0 < self.mask_fin_angle < 90:
            raise ValueError("El ángulo β de aletas debe estar entre 0° y 90°.")
        if self.protractor_step <= 0 or self.protractor_step >= 90:
            raise ValueError("El paso del transportador debe estar entre 1° y 89°.")
        if self.hour_start >= self.hour_end:
            raise ValueError("La hora de inicio debe ser menor que la hora de fin.")
        if not 0 <= self.hour_start <= 23 or not 0 <= self.hour_end <= 23:
            raise ValueError("Las horas deben estar entre 0 y 23.")
        if self.dpi <= 0:
            raise ValueError("El DPI debe ser mayor que 0.")
        if self.sill_height_m < 0:
            raise ValueError("La altura del antepecho no puede ser negativa.")
        if self.window_height_m <= 0:
            raise ValueError("La altura de la ventana debe ser mayor que 0.")
        if self.gap_to_overhang_m < 0:
            raise ValueError("El vano hasta el alero no puede ser negativo.")
        if self.window_width_m <= 0:
            raise ValueError("El ancho de ventana debe ser mayor que 0.")
        if not self.critical_months:
            raise ValueError("Seleccioná al menos un mes del período crítico.")
        if not all(1 <= m <= 12 for m in self.critical_months):
            raise ValueError("Los meses críticos deben estar entre 1 y 12.")
        if self.critical_hour_start >= self.critical_hour_end:
            raise ValueError("La hora crítica de inicio debe ser menor que la de fin.")
        if not 0 <= self.critical_hour_start <= 23 or not 0 <= self.critical_hour_end <= 23:
            raise ValueError("Las horas críticas deben estar entre 0 y 23.")
        if self.timezone_utc_offset is not None and not -12 <= self.timezone_utc_offset <= 14:
            raise ValueError("El huso UTC debe estar entre −12 y +14.")
        if self.device_mode not in DEVICE_MODES:
            raise ValueError("El modo debe ser 'overhang' o 'vertical_fin'.")
        if self.fin_arrangement not in {"bilateral", "single"}:
            raise ValueError("La disposición de aletas debe ser 'bilateral' o 'single'.")
        if self.chart_detail not in {"full", "preview"}:
            raise ValueError("chart_detail debe ser 'full' o 'preview'.")

    @classmethod
    def default(cls) -> "CartaSolarConfig":
        return cls()

    @classmethod
    def for_latitude(cls, lat: float, **kwargs) -> "CartaSolarConfig":
        """Config con meses críticos de verano local según hemisferio."""
        from carta_solar.critical import default_critical_months_for_lat

        months = kwargs.pop("critical_months", default_critical_months_for_lat(lat))
        return cls(lat=lat, critical_months=months, **kwargs)
