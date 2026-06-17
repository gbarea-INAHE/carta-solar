"""Autoría y logos opcionales de la herramienta."""

from __future__ import annotations

from pathlib import Path

AUTHORS = "Dr. Arq. Gustavo Barea — Dra. Carolina Ganem"
INSTITUTION = "INAHE — CONICET"
CREDIT_LINE = f"{AUTHORS}  |  {INSTITUTION}"

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
LOGO_INAHE = ASSETS_DIR / "logo_inahe.png"
LOGO_CONICET = ASSETS_DIR / "logo_conicet.png"


def available_logos() -> list[Path]:
    """Logos presentes en assets/ (opcional)."""
    return [path for path in (LOGO_INAHE, LOGO_CONICET) if path.is_file()]


def add_figure_credit(fig) -> None:
    """Pie de figura exportada con autoría."""
    fig.text(
        0.5,
        0.008,
        CREDIT_LINE,
        ha="center",
        va="bottom",
        fontsize=8,
        color="#444444",
    )
