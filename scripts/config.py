#!/usr/bin/env python3
"""
Configuración global del entorno de estudio.

La carpeta de datos se resuelve en este orden:

1. Variable de entorno ``ESTUDIO_BASE_DIR`` (útil para pruebas y para mover
   los datos a otra unidad).
2. **Modo portable**: si la aplicación viene empaquetada (PyInstaller), los
   datos viven en la carpeta ``datos/`` junto al ejecutable (Windows) o junto
   al ``.app`` (macOS).
3. **Modo desarrollo**: la carpeta histórica del proyecto.

Así el mismo código funciona en la instalación local y en el ZIP que se comparte.
"""
import os
import pathlib
import sys

# Ruta histórica del proyecto (modo desarrollo en Windows)
_DEFAULT_DIR = pathlib.Path(r"C:\Universidad\estudio-psicologia")


def _frozen_base_dir() -> pathlib.Path:
    """Carpeta de datos cuando la app se distribuye empaquetada."""
    executable = pathlib.Path(sys.executable).resolve()
    parts = executable.parts
    # macOS: .../Estudio UTE.app/Contents/MacOS/Estudio UTE -> datos junto al .app
    for index, part in enumerate(parts):
        if part.endswith(".app"):
            return pathlib.Path(*parts[:index]) / "datos"
    # Windows/Linux: .../Estudio UTE/Estudio UTE.exe -> datos junto al ejecutable
    return executable.parent / "datos"


def _resolve_base_dir() -> pathlib.Path:
    override = os.environ.get("ESTUDIO_BASE_DIR", "").strip()
    if override:
        return pathlib.Path(override).expanduser().resolve()
    if getattr(sys, "frozen", False):
        return _frozen_base_dir()
    if os.name == "nt":
        return _DEFAULT_DIR
    return pathlib.Path.home() / "EstudioUTE"


# Ruta base de datos (materias, salidas, recursos del usuario)
BASE_DIR = _resolve_base_dir()

# Subdirectorios
MATERIAS_DIR = BASE_DIR / "materias"
SCRIPTS_DIR = BASE_DIR / "scripts"
RECURSOS_DIR = BASE_DIR / "recursos"
SALIDAS_DIR = BASE_DIR / "salidas"
FUENTES_DIR = BASE_DIR / "fuentes"

# Archivos de referencia
APA7_MANUAL = RECURSOS_DIR / "apa7_manual.md"
README = BASE_DIR / "README.md"


def ensure_dirs():
    """Asegura que los directorios de datos existan.

    No crea ``scripts/``: en el paquete portable el código viaja dentro del
    ejecutable, no en la carpeta de datos.
    """
    for d in [MATERIAS_DIR, RECURSOS_DIR, SALIDAS_DIR, FUENTES_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def get_materia_dir(materia_name):
    """Devuelve la ruta de una materia normalizando el nombre."""
    folder_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in materia_name).strip().replace(" ", "_")
    return MATERIAS_DIR / folder_name


def list_materias():
    """Lista todas las materias existentes."""
    if not MATERIAS_DIR.exists():
        return []
    return [d.name for d in MATERIAS_DIR.iterdir() if d.is_dir()]


def find_materia_dir(name):
    """Encuentra la carpeta de una materia por nombre aproximado."""
    normalized = "".join(c if c.isalnum() or c in " _-" else "_" for c in name).strip().replace(" ", "_")
    candidate = MATERIAS_DIR / normalized
    if candidate.exists():
        return candidate
    # Búsqueda aproximada
    for d in MATERIAS_DIR.iterdir():
        if d.is_dir() and (d.name.lower() == normalized.lower() or d.name.lower().startswith(normalized.lower())):
            return d
    return None
