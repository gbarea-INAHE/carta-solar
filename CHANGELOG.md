# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto adhiere a [Versionado Semántico](https://semver.org/lang/es/).

## [1.2.2] - 2026-09-30

### Fixed

- Parasoles verticales: β automático ya no usa mín |γ| (pegaba ~8°/D≈5 m en N/E/O).
  Ahora usa **percentil P25** de |γ| (estilo SOL-AR), excluye sol casi normal,
  limita profundidad constructiva y reporta β izq/der.
- Streamlit: las horas críticas se resincronizan al cambiar el azimut de fachada
  (E → 7–12, O → 12–18).

### Added

- `suggested_critical_hours`, `describe_fin_design`, tests de rotación de máscara
  y de diferenciación N/E/S.

## [1.2.0] - 2026-09-30

### Added

- Azimut de fachada libre (N/E/S/O o personalizado); transportador SOL-AR rotado.
- Modo **parasol vertical** (ángulo β / profundidad D) con planta esquemática.
- Selector de dispositivo en Streamlit + sugerencia bioclimática E/O → vertical.
- Vista previa rápida (`chart_detail=preview`) y PNG 300 dpi bajo demanda.
- Paquete `carta_solar/devices/` (alero y aletas).

### Changed

- Sector crítico por ángulo γ (frente a fachada), sin amarrar a N/S en la carta.
- Requisitos: Python 3.11+.

### Notes

- DOI de versión Zenodo: [10.5281/zenodo.23050230](https://doi.org/10.5281/zenodo.23050230).
- Próximamente: louvres horizontales y obstrucciones del entorno.

## [1.1.1] - 2026-09-30

### Fixed

- Streamlit: la carta se regenera al cambiar parámetros del formulario
  (antes quedaba congelada en `session_state` hasta pulsar el botón).

### Added

- Horas civiles (reloj) convertidas a solares con longitud, huso UTC y ecuación
  del tiempo (`civil_to_solar_hour`); activable en las UIs.
- CI GitHub Actions (`pytest` en Python 3.11 y 3.12).
- DOI de versión Zenodo: [10.5281/zenodo.23050120](https://doi.org/10.5281/zenodo.23050120).

## [1.1.0] - 2026-09-30

### Added

- DOI de versión Zenodo: [10.5281/zenodo.23049955](https://doi.org/10.5281/zenodo.23049955)
  (concepto: [10.5281/zenodo.20725118](https://doi.org/10.5281/zenodo.20725118)).

### Fixed

- Criterio de sombreado invertido en `is_point_shaded_by_alpha`: el informe y los
  marcadores ahora coinciden con la máscara SOL-AR y la física del alero
  (Ñacuñán verano: 65/65 cubierto).
- Fuga de memoria en Streamlit/tkinter: se cierra la figura previa al recalcular
  y el PNG de descarga se cachea en `session_state`.

### Changed

- α de diseño = mínimo ángulo de perfil ε sobre el período crítico
  (`compute_required_alpha`), no la altitud de mediodía.
- `apply_computed_mask` usa `dataclasses.replace`.
- Marcadores expuesto/protegido con paleta Okabe–Ito y formas distintas (× / ○).
- Dependencias fijadas en `requirements.txt`.
- Documentación y capturas regeneradas; `.gitignore` permite `docs/*.png`.

### Added

- Soporte de fachada ecuatorial: Norte (HS) / Sur (HN) según signo de latitud,
  con transportador reflejado y meses de verano local por defecto.
- `profile_angle`, `alt_az_from_xy` y validaciones de UI (lat/lon, nombre de sitio).
- Longitud mostrada en la carta como metadatos (no entra en el cálculo solar).

## [1.0.4] - 2026-06-17

### Added

- App web publicada en [Streamlit Cloud](https://carta-solar.streamlit.app/).

### Changed

- README y DEPLOYMENT con URL de la aplicación en línea.

## [1.0.3] - 2026-06-17

### Added

- Capturas de pantalla reales en `docs/carta_solar.png` y `docs/alero_norte.png`.

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

[1.2.0]: https://github.com/gbarea-INAHE/carta-solar/compare/v1.1.1...v1.2.0
[1.1.1]: https://github.com/gbarea-INAHE/carta-solar/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/gbarea-INAHE/carta-solar/compare/v1.0.4...v1.1.0
[1.0.4]: https://github.com/gbarea-INAHE/carta-solar/compare/v1.0.3...v1.0.4
[1.0.3]: https://github.com/gbarea-INAHE/carta-solar/compare/v1.0.2...v1.0.3
[1.0.2]: https://github.com/gbarea-INAHE/carta-solar/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/gbarea-INAHE/carta-solar/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/gbarea-INAHE/carta-solar/releases/tag/v1.0.0
