# Carta Solar

Generador de cartas solares estereográficas con interfaz gráfica y cálculo de aleros en fachada norte.

**Autoría:** Dr. Arq. Gustavo Barea — Dra. Carolina Ganem  
**Institución:** INAHE — CONICET

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## App web (Streamlit)

Versión en navegador, sin instalar Python:

**Repositorio:** [github.com/gbarea-INAHE/carta-solar](https://github.com/gbarea-INAHE/carta-solar)

**URL app web:** _pendiente — desplegar en [Streamlit Cloud](https://share.streamlit.io) (ver [DEPLOYMENT.md](DEPLOYMENT.md))_

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## App de escritorio (tkinter)

```bash
pip install -r requirements.txt
python app.py
```

## Cómo citar

DOI Zenodo: [10.5281/zenodo.20725119](https://doi.org/10.5281/zenodo.20725119)

```bibtex
@software{barea2026carta_solar,
  author = {Barea, Gustavo and Ganem, Carolina},
  title = {Carta Solar — Aleros Norte},
  year = {2026},
  publisher = {Zenodo},
  doi = {10.5281/zenodo.20725119},
  url = {https://github.com/gbarea-INAHE/carta-solar}
}
```

También podés usar el archivo [CITATION.cff](CITATION.cff).

## Requisitos

- Python 3.10+
- Dependencias en `requirements.txt`

## Flujo de trabajo (dimensionamiento de alero norte)

1. Ingresá **latitud** y las **medidas en corte vertical**:
   - **Antepecho** `h_s`: piso → inicio de ventana
   - **Altura ventana** `h_v`
   - **Vano** `h_g`: cierre superior de ventana → inicio del alero
2. Elegí meses y horas del **período crítico** (verano).
3. Pulsá **Calcular alero**: el programa toma **α = altitud solar mínima al mediodía** entre los meses seleccionados (donde las trayectorias cortan los círculos en el eje Norte) y calcula **P = (h_v + h_g) / tan(α)**.
4. Revisá el **informe de cobertura**, la carta con transportador y el **diagrama en sección**.
5. Guardá o descargá PNG/PDF.

El antepecho `h_s` solo se usa en el dibujo en sección; no entra en el cálculo de α ni de P.

## Publicación (GitHub, Zenodo, web)

Instrucciones completas en **[DEPLOYMENT.md](DEPLOYMENT.md)**:

1. Push a GitHub público
2. Release en GitHub → DOI en Zenodo ([10.5281/zenodo.20725119](https://doi.org/10.5281/zenodo.20725119))
3. Deploy gratuito en [Streamlit Cloud](https://share.streamlit.io)

## Tests

```bash
python -m pytest tests/ -v
```

## Estructura

```
carta_solar/      # núcleo: cálculos, transportador, carta, alero
app.py            # GUI tkinter (escritorio)
streamlit_app.py  # GUI web (Streamlit)
assets/           # logos opcionales
tests/
DEPLOYMENT.md     # guía Zenodo + Streamlit Cloud
CITATION.cff      # metadatos de citación
LICENSE           # MIT
```

### Logos (opcional)

Colocá en `assets/`:

- `logo_inahe.png`
- `logo_conicet.png`

## Licencia

MIT — ver [LICENSE](LICENSE).
