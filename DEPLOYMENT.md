# Publicación: GitHub, Zenodo (DOI) y Streamlit Cloud

Guía paso a paso para publicar **Carta Solar — Aleros Norte**.

## 1. Crear repositorio en GitHub

1. Entrá a [github.com/new](https://github.com/new)
2. Nombre sugerido: `carta-solar`
3. Repositorio **público**, sin README inicial (ya está en el proyecto local)
4. Copiá la URL del remoto, por ejemplo:
   `https://github.com/TU_USUARIO/carta-solar.git`

## 2. Subir el código

Desde `F:\ProgramasIA\Carta_Solar`:

```powershell
git remote add origin https://github.com/TU_USUARIO/carta-solar.git
git branch -M main
git push -u origin main
```

Reemplazá `TU_USUARIO` por tu cuenta de GitHub.

Actualizá las URLs en `CITATION.cff` y `README.md` con tu usuario real.

## 3. Obtener DOI en Zenodo

1. Creá cuenta en [zenodo.org](https://zenodo.org) (recomendado vincular ORCID)
2. **Account → GitHub** → conectar y autorizar Zenodo
3. En la lista de repositorios, activá **carta-solar**
4. En GitHub, creá un **Release**:
   - Tag: `v1.0.0`
   - Título: `v1.0.0 — Primera versión publicada`
   - Descripción breve del software
5. Zenodo creará un registro en unos minutos y asignará un DOI (`10.5281/zenodo.XXXXXXX`)
6. Copiá el DOI y actualizá:
   - `CITATION.cff` → campo `doi`
   - `README.md` → sección **Cómo citar**
7. Commit y push; opcionalmente un release `v1.0.1` solo con metadatos actualizados

## 4. Desplegar app web (Streamlit Cloud, gratis)

1. Entrá a [share.streamlit.io](https://share.streamlit.io) con tu cuenta GitHub
2. **Create app**
3. Repositorio: `TU_USUARIO/carta-solar`
4. Branch: `main`
5. Main file: `streamlit_app.py`
6. **Deploy**
7. La URL será similar a: `https://carta-solar-TU_USUARIO.streamlit.app`
8. Actualizá `README.md` → sección **App web** con la URL real

## 5. Probar localmente la versión web

```powershell
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## 6. Cómo citar (plantilla)

```bibtex
@software{barea2026carta_solar,
  author = {Barea, Gustavo and Ganem, Carolina},
  title = {Carta Solar — Aleros Norte},
  year = {2026},
  publisher = {Zenodo},
  doi = {10.5281/zenodo.XXXXXXX},
  url = {https://github.com/TU_USUARIO/carta-solar}
}
```

Reemplazá `XXXXXXX` y `TU_USUARIO` tras publicar.
