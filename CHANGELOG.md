# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto adhiere a [Versionado Semántico](https://semver.org/lang/es/).

## [1.0.2] - 2026-06-17

### Changed

- Actualización de README con badges, tabla resumen y sección de citación académica.
- Mejora de metadatos de citación en `CITATION.cff` y `.zenodo.json`.
- Documentación visual en `docs/` con placeholders para capturas de pantalla.

## [1.0.1] - 2026-06-16

### Added

- Integración con Zenodo mediante release de GitHub.
- DOI asignado: [10.5281/zenodo.20725119](https://doi.org/10.5281/zenodo.20725119).

### Changed

- Correcciones de documentación (`README.md`, `DEPLOYMENT.md`, `CITATION.cff`).

## [1.0.0] - 2026-06-16

### Added

- Primera publicación del software.
- Generación de carta solar estereográfica con transportador SOL-AR.
- Trayectorias solares mensuales y líneas horarias.
- Máscara de obstrucción según período crítico de insolación.
- Cálculo de profundidad de alero en fachada norte (**P = H_eff / tan(α)**).
- Interfaz gráfica de escritorio (`app.py`, tkinter).
- Interfaz web (`streamlit_app.py`, Streamlit).
- Suite de tests con `pytest`.

[1.0.2]: https://github.com/gbarea-INAHE/carta-solar/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/gbarea-INAHE/carta-solar/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/gbarea-INAHE/carta-solar/releases/tag/v1.0.0
