import re
import unicodedata


def decimal_to_dms(decimal_deg: float) -> tuple[int, int, float]:
    sign = 1 if decimal_deg >= 0 else -1
    absolute = abs(decimal_deg)
    degrees_part = int(absolute)
    minutes_float = (absolute - degrees_part) * 60
    minutes_part = int(minutes_float)
    seconds_part = (minutes_float - minutes_part) * 60
    return sign * degrees_part, minutes_part, seconds_part


def format_lat_lon(lat: float, lon: float) -> tuple[str, str]:
    lat_deg, lat_min, _ = decimal_to_dms(lat)
    lon_deg, lon_min, _ = decimal_to_dms(lon)

    lat_hem = "N" if lat >= 0 else "S"
    lon_hem = "E" if lon >= 0 else "O"

    lat_str = f"{abs(lat_deg)}°{lat_min:02d}′{lat_hem}"
    lon_str = f"{abs(lon_deg)}°{lon_min:02d}′{lon_hem}"
    return lat_str, lon_str


def site_slug(site_name: str) -> str:
    normalized = unicodedata.normalize("NFKD", site_name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_name.strip().lower())
    return slug.strip("_") or "sitio"
