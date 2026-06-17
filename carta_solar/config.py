from dataclasses import dataclass, field
from pathlib import Path

from carta_solar.critical import DEFAULT_CRITICAL_MONTHS


@dataclass
class CartaSolarConfig:
    site_name: str = "Ñacuñán"
    lat: float = -34.0333
    lon: float = -67.9167
    mask_alt: float | None = None
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
    critical_months: frozenset[int] = field(default_factory=lambda: DEFAULT_CRITICAL_MONTHS)
    critical_hour_start: int = 10
    critical_hour_end: int = 18
    highlight_critical_period: bool = True

    def __post_init__(self) -> None:
        self.output_dir = Path(self.output_dir)
        self.critical_months = frozenset(self.critical_months)
        self.validate()

    @property
    def effective_shading_height_m(self) -> float:
        """Altura desde dintel inferior de ventana hasta el alero (h_v + h_g)."""
        return self.window_height_m + self.gap_to_overhang_m

    @property
    def total_wall_height_m(self) -> float:
        return self.sill_height_m + self.window_height_m + self.gap_to_overhang_m

    def validate(self) -> None:
        if not self.site_name.strip():
            raise ValueError("El nombre del sitio no puede estar vacío.")
        if not -90 <= self.lat <= 90:
            raise ValueError("La latitud debe estar entre -90° y 90°.")
        if not -180 <= self.lon <= 180:
            raise ValueError("La longitud debe estar entre -180° y 180°.")
        if self.mask_alt is not None and not 0 < self.mask_alt < 90:
            raise ValueError("El ángulo α calculado debe estar entre 0° y 90°.")
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
        if not self.critical_months:
            raise ValueError("Seleccioná al menos un mes del período crítico.")
        if not all(1 <= m <= 12 for m in self.critical_months):
            raise ValueError("Los meses críticos deben estar entre 1 y 12.")
        if self.critical_hour_start >= self.critical_hour_end:
            raise ValueError("La hora crítica de inicio debe ser menor que la de fin.")
        if not 0 <= self.critical_hour_start <= 23 or not 0 <= self.critical_hour_end <= 23:
            raise ValueError("Las horas críticas deben estar entre 0 y 23.")

    @classmethod
    def default(cls) -> "CartaSolarConfig":
        return cls()
