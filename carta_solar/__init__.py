"""Carta Solar — cartas estereográficas y dispositivos de sombreado."""

from __future__ import annotations

from typing import Any

__version__ = "1.2.1"

__all__ = [
    "CartaSolarConfig",
    "generate_carta_solar",
    "save_carta_solar",
    "__version__",
]


def __getattr__(name: str) -> Any:
    """Carga diferida: evita imports pesados/circulares al importar submódulos."""
    if name == "CartaSolarConfig":
        from carta_solar.config import CartaSolarConfig

        return CartaSolarConfig
    if name == "generate_carta_solar":
        from carta_solar.plot import generate_carta_solar

        return generate_carta_solar
    if name == "save_carta_solar":
        from carta_solar.plot import save_carta_solar

        return save_carta_solar
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
