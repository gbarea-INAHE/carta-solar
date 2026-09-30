from math import asin, atan, atan2, cos, degrees, radians, sin, tan

import numpy as np


def declination(day: int | float) -> float:
    return 23.45 * np.sin(np.radians(360 * (284 + day) / 365.0))


def equation_of_time_minutes(day: int | float) -> float:
    """Ecuación del tiempo (minutos): solar − civil media, aproximación clásica."""
    b = radians(360.0 * (float(day) - 81.0) / 365.0)
    return 9.87 * sin(2 * b) - 7.53 * cos(b) - 1.5 * sin(b)


def estimate_timezone_utc(lon_deg: float) -> float:
    """Offset UTC estimado por huso geográfico (múltiplos de 15°)."""
    return float(round(lon_deg / 15.0))


def civil_to_solar_hour(
    hour_civil: float,
    lon_deg: float,
    day: int | float,
    timezone_utc_hours: float | None = None,
) -> float:
    """
    Hora solar a partir de hora civil (reloj local).

    solar = civil + (lon − lon_std)/15 + EoT/60
    con lon positiva al Este y lon_std = 15 × UTC_offset.
    """
    if timezone_utc_hours is None:
        timezone_utc_hours = estimate_timezone_utc(lon_deg)
    lon_std = 15.0 * timezone_utc_hours
    eot_hours = equation_of_time_minutes(day) / 60.0
    return hour_civil + (lon_deg - lon_std) / 15.0 + eot_hours


def solar_alt_az(lat_deg: float, day: int | float, hour_solar: float) -> tuple[float, float]:
    """
    Altitude and azimuth.
    Azimuth: 0° = Norte, 90° = Este, 180° = Sur, 270° = Oeste.
    Corrected for southern hemisphere: at solar noon below the equator, the sun is to the North.
    """
    phi = radians(lat_deg)
    delta = radians(declination(day))
    H = radians(15 * (hour_solar - 12))

    sin_alt = sin(phi) * sin(delta) + cos(phi) * cos(delta) * cos(H)
    sin_alt = max(-1, min(1, sin_alt))
    alt = asin(sin_alt)

    az = (degrees(atan2(sin(H), cos(H) * sin(phi) - tan(delta) * cos(phi))) + 180) % 360
    return degrees(alt), az


def solar_alt_az_at_clock(
    lat_deg: float,
    lon_deg: float,
    day: int | float,
    hour_clock: float,
    *,
    use_civil_hours: bool = False,
    timezone_utc_hours: float | None = None,
) -> tuple[float, float]:
    """alt/az para hora de reloj; si use_civil_hours, convierte con lon y EoT."""
    hour_solar = hour_clock
    if use_civil_hours:
        hour_solar = civil_to_solar_hour(
            hour_clock, lon_deg, day, timezone_utc_hours
        )
    return solar_alt_az(lat_deg, day, hour_solar)


def r_from_alt(alt_deg: float) -> float:
    """Stereographic projection: horizon = 1, zenith = 0."""
    return float(np.tan(np.radians((90 - alt_deg) / 2)))


def xy_from_alt_az(alt: float, az: float) -> tuple[float, float]:
    r = r_from_alt(alt)
    theta = np.radians(az)
    x = r * np.sin(theta)
    y = r * np.cos(theta)
    return float(x), float(y)


def alt_az_from_xy(x: float, y: float) -> tuple[float, float]:
    """Inversa de la proyección estereográfica (horizonte = 1, cenit = 0)."""
    r = float(np.hypot(x, y))
    alt = 90.0 - 2.0 * degrees(atan(r))
    az = float(degrees(atan2(x, y)) % 360.0)
    return alt, az


def signed_bearing_diff(az: float, facade_az: float) -> float:
    """Ángulo firmado γ ∈ (-180, 180] entre el azimut solar y la normal de fachada."""
    return ((az - facade_az + 180.0) % 360.0) - 180.0


def profile_angle(
    alt: float,
    az: float,
    facade_az: float = 0.0,
) -> float | None:
    """
    Ángulo de perfil ε (°) para un alero horizontal frente a `facade_az`.

    tan ε = tan h / cos γ, con γ = az − facade_az.
    Devuelve None si alt ≤ 0 o el sol está detrás de la fachada (cos γ ≤ 0).
    """
    if alt <= 0:
        return None
    gamma = radians(signed_bearing_diff(az, facade_az))
    cos_g = cos(gamma)
    if cos_g <= 0:
        return None
    tan_eps = tan(radians(alt)) / cos_g
    return degrees(atan(tan_eps))


def profile_angle_north(alt: float, az: float) -> float | None:
    """Ángulo de perfil para fachada norte (facade_az = 0°)."""
    return profile_angle(alt, az, facade_az=0.0)
