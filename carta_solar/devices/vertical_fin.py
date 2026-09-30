"""Parasol vertical — aletas cortas (N, D, S, rotación) estilo obra / SOL-AR."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

import numpy as np

from carta_solar.config import CartaSolarConfig
from carta_solar.critical import (
    MONTH_NAMES,
    collect_critical_samples,
    default_critical_months_for_lat,
    facade_azimuth_for_lat,
)
from carta_solar.solar import signed_bearing_diff

# Percentil de |γ| para el ángulo de corte requerido (P25 ≈ cubrir el 75 % más oblicuo).
DEFAULT_BETA_PERCENTILE = 25.0
# Sol casi normal: no sombreable solo con aletas (aviso / exclusión del percentil).
NEAR_NORMAL_DEG = 15.0
# Profundidad máxima del modelo antiguo (una sola aleta profunda); queda como ref. secundaria.
DEFAULT_MAX_DEPTH_M = 2.5
# Profundidad de aleta corta por defecto (obra).
DEFAULT_FIN_DEPTH_M = 0.50
# Tope de rotación constructiva sobre el eje de la aleta (±).
DEFAULT_MAX_ROTATION_DEG = 45.0
# Si |mediana γ| es menor, se considera simétrico → rotación 0°.
ROTATION_SYMMETRY_TOL_DEG = 8.0


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
    Protegido por banco de aletas con ángulo de corte φ ⇔ |γ| ≥ φ
    (o detrás de fachada).

    φ pequeño ⇒ separación chica (o D grande) ⇒ más protección.
    """
    phi = horizontal_shadow_angle(az, facade_az)
    if phi is None:
        return True
    return phi + 1e-6 >= beta_deg


def cut_angle_from_spacing(depth_m: float, spacing_m: float) -> float:
    """
    Ángulo de corte en planta φ (°) para aletas perpendiculares a la fachada.

    Geometría en planta (centros a distancia S, proyección D desde el muro)::

        tan(φ) = S / D  ⇒  φ = arctan(S / D)

    Los rayos con |γ| ≥ φ quedan bloqueados por el banco de aletas.
    """
    if depth_m <= 0:
        raise ValueError("La profundidad de aleta debe ser mayor que 0.")
    if spacing_m < 0:
        raise ValueError("La separación entre aletas no puede ser negativa.")
    if spacing_m == 0:
        return 0.0
    return math.degrees(math.atan(spacing_m / depth_m))


def spacing_from_cut_angle(depth_m: float, cut_angle_deg: float) -> float:
    """Separación máxima entre centros S = D · tan(φ) para un φ de diseño."""
    if depth_m <= 0:
        raise ValueError("La profundidad de aleta debe ser mayor que 0.")
    if not 0 <= cut_angle_deg < 90:
        raise ValueError("El ángulo de corte debe estar entre 0° y 90°.")
    return depth_m * math.tan(math.radians(cut_angle_deg))


def fin_count_for_width(window_width_m: float, max_spacing_m: float) -> int:
    """
    Cantidad de aletas N para vano de ancho W con separación máxima S_max.

    Criterio: aletas en ambos jambas + intermedias equiespaciadas entre centros::

        N = ceil(W / S_max) + 1   (mínimo 2)

    Luego la separación real es S = W / (N − 1) ≤ S_max.
    """
    if window_width_m <= 0:
        raise ValueError("El ancho de ventana debe ser mayor que 0.")
    if max_spacing_m <= 0:
        # Separación nula ⇒ tantas aletas como haga falta conceptualmente;
        # en la práctica devolvemos un piso alto acotado por W cm a cm.
        return max(2, int(math.ceil(window_width_m / 0.05)) + 1)
    n = int(math.ceil(window_width_m / max_spacing_m)) + 1
    return max(2, n)


def spacing_from_count(window_width_m: float, n_fins: int) -> float:
    """Separación entre centros S = W / (N − 1)."""
    if window_width_m <= 0:
        raise ValueError("El ancho de ventana debe ser mayor que 0.")
    if n_fins < 2:
        raise ValueError("Se necesitan al menos 2 aletas (jambas).")
    return window_width_m / (n_fins - 1)


def fin_depth_from_angle(
    window_width_m: float,
    beta_deg: float,
    *,
    bilateral: bool = True,
) -> float:
    """
    Profundidad D (m) del modelo de **una** aleta profunda (referencia secundaria).

    Bilateral: D = (W/2) / tan(β); unilateral: D = W / tan(β).
    El diseño principal usa aletas cortas fijas (ver ``design_short_fins``).
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
    """β mínimo (°) para no superar max_depth_m (modelo de aleta profunda)."""
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
    """Ángulo de corte requerido φ (percentil de |γ|); dato técnico interno."""

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
    signed_gammas: tuple[float, ...] = ()


@dataclass(frozen=True)
class ShortFinDesign:
    """Paquete de aletas cortas para obra (resultado principal)."""

    depth_m: float
    spacing_m: float
    n_fins: int
    cut_angle_deg: float
    rotation_deg: float
    required_cut_angle_deg: float
    samples: list
    limiting_month: int | None
    n_frontal: int
    n_near_normal: int
    coverage_frac: float
    percentile: float
    rotation_left_deg: float | None = None
    rotation_right_deg: float | None = None
    deep_fin_depth_m: float | None = None

    @property
    def beta_deg(self) -> float:
        """Alias técnico: ángulo de corte en planta (= mask_fin_angle)."""
        return self.cut_angle_deg


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
    φ de diseño por percentil de |γ| (estilo SOL-AR: no forzar mín |γ|).

    - Toma muestras frontales del período crítico.
    - Excluye sol casi normal (|γ| < near_normal_deg) del percentil.
    - φ = percentil(φ usable); opcionalmente se eleva a ``min_beta_deg``.
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
    signed_gammas: list[float] = []
    n_near = 0
    limiting_month: int | None = None
    limiting_phi = float("inf")

    for s in samples:
        gamma = signed_horizontal_gamma(s.az, facade_az)
        if gamma is None:
            continue
        phi = abs(gamma)
        frontal_phi.append(phi)
        signed_gammas.append(gamma)
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
            signed_gammas=tuple(signed_gammas),
        )

    source = usable_phi if usable_phi else frontal_phi
    beta = _percentile_phi(source, percentile)
    capped = False
    if min_beta_deg is not None and beta < min_beta_deg:
        beta = float(min_beta_deg)
        capped = True

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
        signed_gammas=tuple(signed_gammas),
    )


def recommended_fin_rotation(
    signed_gammas: list[float] | tuple[float, ...],
    *,
    max_abs_deg: float = DEFAULT_MAX_ROTATION_DEG,
    symmetry_tol_deg: float = ROTATION_SYMMETRY_TOL_DEG,
) -> tuple[float, float | None, float | None]:
    """
    Rotación recomendada del plano de la aleta respecto a la normal de fachada.

    0° = perpendicular a la fachada («de canto» saliente).
    Signo: positivo hacia +γ (derecha en planta local); negativo hacia −γ.
    Se toma la mediana de γ firmados y se limita a ±max_abs_deg.
    Si |mediana| < symmetry_tol → 0° (banco simétrico).
    """
    if not signed_gammas:
        return 0.0, None, None
    arr = np.asarray(signed_gammas, dtype=float)
    median = float(np.median(arr))
    left = arr[arr < 0]
    right = arr[arr > 0]
    rot_left = float(np.median(left)) if len(left) else None
    rot_right = float(np.median(right)) if len(right) else None
    if abs(median) < symmetry_tol_deg:
        return 0.0, rot_left, rot_right
    clamped = max(-max_abs_deg, min(max_abs_deg, median))
    return clamped, rot_left, rot_right


def design_short_fins(
    lat: float,
    months: frozenset[int],
    hour_start: int,
    hour_end: int,
    window_width_m: float,
    depth_m: float = DEFAULT_FIN_DEPTH_M,
    *,
    facade_az: float | None = None,
    lon: float = 0.0,
    use_civil_hours: bool = False,
    timezone_utc_hours: float | None = None,
    percentile: float = DEFAULT_BETA_PERCENTILE,
    near_normal_deg: float = NEAR_NORMAL_DEG,
    max_rotation_deg: float = DEFAULT_MAX_ROTATION_DEG,
) -> ShortFinDesign:
    """
    Dimensiona un banco de aletas cortas de proyección fija D.

    1. φ_req = percentil de |γ| en el período crítico (excl. sol casi normal).
    2. S_max = D · tan(φ_req).
    3. N = ceil(W / S_max) + 1 (incluye jambas); S = W / (N − 1).
    4. φ_eff = arctan(S / D) ≤ φ_req.
    5. Rotación θ = mediana(γ) acotada a ±max_rotation_deg (0° si simétrico).
    """
    if depth_m <= 0:
        raise ValueError("La profundidad de cada aleta debe ser mayor que 0.")
    if window_width_m <= 0:
        raise ValueError("El ancho de ventana debe ser mayor que 0.")

    angle = compute_required_fin_angle(
        lat,
        months,
        hour_start,
        hour_end,
        facade_az=facade_az,
        lon=lon,
        use_civil_hours=use_civil_hours,
        timezone_utc_hours=timezone_utc_hours,
        percentile=percentile,
        near_normal_deg=near_normal_deg,
        min_beta_deg=None,
    )
    phi_req = angle.beta_deg
    if angle.n_frontal == 0:
        # Sin sol frontal: dos aletas laterales bastan; φ = 90° (máscara nula).
        n_fins = 2
        spacing = window_width_m
        cut = 90.0
    else:
        s_max = spacing_from_cut_angle(depth_m, min(phi_req, 89.9))
        n_fins = fin_count_for_width(window_width_m, s_max)
        spacing = spacing_from_count(window_width_m, n_fins)
        cut = cut_angle_from_spacing(depth_m, spacing)

    rotation, rot_l, rot_r = recommended_fin_rotation(
        angle.signed_gammas, max_abs_deg=max_rotation_deg
    )

    # Cobertura con el φ efectivo del banco (no el de una sola aleta profunda).
    frontal_phis = [
        abs(g) for g in angle.signed_gammas if abs(g) <= 90.0 + 1e-9
    ]
    if frontal_phis:
        covered = sum(1 for phi in frontal_phis if phi + 1e-6 >= cut)
        coverage = covered / len(frontal_phis)
    else:
        coverage = 1.0

    deep_ref = None
    if 0 < phi_req < 90:
        deep_ref = fin_depth_from_angle(window_width_m, phi_req, bilateral=True)

    return ShortFinDesign(
        depth_m=float(depth_m),
        spacing_m=float(spacing),
        n_fins=int(n_fins),
        cut_angle_deg=float(cut),
        rotation_deg=float(rotation),
        required_cut_angle_deg=float(phi_req),
        samples=angle.samples,
        limiting_month=angle.limiting_month,
        n_frontal=angle.n_frontal,
        n_near_normal=angle.n_near_normal,
        coverage_frac=float(coverage),
        percentile=percentile,
        rotation_left_deg=rot_l,
        rotation_right_deg=rot_r,
        deep_fin_depth_m=deep_ref,
    )


def design_short_fins_from_config(
    config: CartaSolarConfig,
    *,
    percentile: float = DEFAULT_BETA_PERCENTILE,
) -> ShortFinDesign:
    """Atajo: lee D, W y período crítico desde la config."""
    return design_short_fins(
        config.lat,
        config.critical_months,
        config.critical_hour_start,
        config.critical_hour_end,
        config.window_width_m,
        config.fin_depth_m,
        facade_az=config.facade_azimuth,
        lon=config.lon,
        use_civil_hours=config.use_civil_hours,
        timezone_utc_hours=config.timezone_utc_offset,
        percentile=percentile,
    )


def compute_vertical_fin_design(
    config: CartaSolarConfig,
    *,
    percentile: float = DEFAULT_BETA_PERCENTILE,
    max_depth_m: float = DEFAULT_MAX_DEPTH_M,
) -> tuple[float, float, int | None]:
    """
    Retorna (ángulo_de_corte_°, profundidad_D_m, mes_limitante).

    ``max_depth_m`` se ignora en el modelo de aletas cortas (queda por
    compatibilidad de firma); D sale de ``config.fin_depth_m``.
    """
    del max_depth_m  # modelo corto: D lo fija la obra, no un tope de aleta única
    design = design_short_fins_from_config(config, percentile=percentile)
    if design.n_frontal == 0:
        raise ValueError(
            "No hay muestras frontales para dimensionar aletas verticales. "
            "Probá horas de mañana (Este) o tarde (Oeste), o combiná con alero."
        )
    return design.cut_angle_deg, design.depth_m, design.limiting_month


def describe_fin_design(
    config: CartaSolarConfig,
    *,
    percentile: float = DEFAULT_BETA_PERCENTILE,
    max_depth_m: float = DEFAULT_MAX_DEPTH_M,
) -> ShortFinDesign:
    """Dimensionamiento de aletas cortas con estadísticas (informe UI)."""
    del max_depth_m
    return design_short_fins_from_config(config, percentile=percentile)


def apply_vertical_fin_design(config: CartaSolarConfig) -> CartaSolarConfig:
    """Copia con mask_fin_angle = φ_eff del banco; mask_alt = None."""
    design = design_short_fins_from_config(config)
    if design.n_frontal == 0:
        raise ValueError(
            "No hay muestras frontales para dimensionar aletas verticales. "
            "Probá horas de mañana (Este) o tarde (Oeste), o combiná con alero."
        )
    return replace(
        config,
        mask_fin_angle=design.cut_angle_deg,
        mask_alt=None,
        fin_spacing_m=design.spacing_m,
        fin_count=design.n_fins,
        fin_rotation_deg=design.rotation_deg,
    )


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


def _fmt_es(value: float, decimals: int = 2) -> str:
    """Número con coma decimal (español)."""
    return f"{value:.{decimals}f}".replace(".", ",")


def _period_phrase(lat: float, months: frozenset[int]) -> str:
    summer = default_critical_months_for_lat(lat)
    if months and months.issubset(summer):
        return "en verano"
    names = [MONTH_NAMES[m] for m in sorted(months)]
    if len(names) <= 3:
        return f"en {', '.join(names)}"
    return "en los meses indicados"


def format_architect_fin_report(
    config: CartaSolarConfig,
    design: ShortFinDesign,
    *,
    unprotected: list | None = None,
) -> str:
    """
    Informe de cobertura coloquial para arquitectos (español profesional).

    Función pura: no depende de Streamlit.
    """
    orient = config.facade_label
    w = _fmt_es(config.window_width_m)
    h = _fmt_es(config.window_height_m)
    n = design.n_fins
    d = _fmt_es(design.depth_m)
    s_cm = _fmt_es(design.spacing_m * 100.0, 0)
    rot = _fmt_es(abs(design.rotation_deg), 0)
    period = _period_phrase(config.lat, config.critical_months)
    h1 = config.critical_hour_start
    h2 = config.critical_hour_end

    if abs(design.rotation_deg) < 0.5:
        rot_clause = "perpendiculares a la fachada (sin rotar)"
    else:
        sentido = "hacia la derecha en planta" if design.rotation_deg > 0 else "hacia la izquierda en planta"
        rot_clause = f"rotados {rot}° sobre su eje ({sentido})"

    lines = [
        (
            f"Para la orientación {orient} y la ventana de {w} m × {h} m, "
            f"para cubrir {period} entre las {h1:02d} h y las {h2:02d} h "
            f"hacen falta {n} parasoles de {d} m de proyección, "
            f"separados {s_cm} cm entre centros, {rot_clause}."
        ),
        (
            f"Ángulo de corte en planta del banco: {_fmt_es(design.cut_angle_deg, 1)}° "
            f"(separación S = D·tan φ). "
            f"Cobertura estimada del período: {100.0 * design.coverage_frac:.0f}% "
            f"de las posiciones solares frontales."
        ),
    ]
    if design.n_near_normal > 0:
        lines.append(
            f"Hay {design.n_near_normal} posiciones con sol casi de frente "
            f"(|γ| < {NEAR_NORMAL_DEG:g}°): las aletas verticales casi no las "
            f"bloquean; conviene combinar con alero u otro dispositivo."
        )
    if design.deep_fin_depth_m is not None and design.deep_fin_depth_m > design.depth_m * 1.5:
        lines.append(
            f"Nota técnica: una sola aleta profunda para el mismo corte pediría "
            f"unos {_fmt_es(design.deep_fin_depth_m)} m de proyección; "
            f"por eso se propone el banco de aletas cortas."
        )
    if unprotected:
        lines.append("Posiciones aún expuestas (revisar o ajustar D / horas):")
        for s in unprotected[:8]:
            lines.append(f"  • {s.label()}")
    elif design.n_frontal > 0:
        lines.append(
            "En el rango horario indicado, el banco cubre las posiciones "
            "oblicuas según el criterio de corte en planta."
        )
    return "\n".join(lines)
