from math import asin, atan2, cos, degrees, radians, sin, tan

import numpy as np


def declination(day: int | float) -> float:
    return 23.45 * np.sin(np.radians(360 * (284 + day) / 365.0))


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


def r_from_alt(alt_deg: float) -> float:
    """Stereographic projection: horizon = 1, zenith = 0."""
    return float(np.tan(np.radians((90 - alt_deg) / 2)))


def xy_from_alt_az(alt: float, az: float) -> tuple[float, float]:
    r = r_from_alt(alt)
    theta = np.radians(az)
    x = r * np.sin(theta)
    y = r * np.cos(theta)
    return float(x), float(y)
