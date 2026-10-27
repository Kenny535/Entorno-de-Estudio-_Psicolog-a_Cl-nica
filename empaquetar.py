#!/usr/bin/env python3
"""
Construye el paquete portable «Estudio UTE» para la plataforma actual.

Lee `empaquetado/especificacion.json` y produce:

    dist/Estudio UTE/            (Windows/Linux)  o  dist/Estudio UTE/Estudio UTE.app (macOS)
        Estudio UTE(.exe)        punto de entrada, sin consola
        datos/                   materia de ejemplo, recursos y todo lo que escriba el usuario
        LEEME.md                 instrucciones para quien lo recibe
        paquete.json             manifiesto legible por una persona o un agente
    dist/Estudio-UTE-<version>-<plataforma>-portable.zip

Uso:
    python empaquetar.py              # construye y comprime
    python empaquetar.py --sin-zip    # sólo la carpeta
    python empaquetar.py --limpiar    # borra build/ y dist/ y sale

Requisitos:
    pip install pyinstaller
    (el resto de dependencias ya las usa la aplicación)

Nota honesta: PyInstaller no compila de forma cruzada. El ZIP de Windows se
construye en Windows y el de macOS en un Mac; este script hace lo correcto en
cada uno, pero aquí sólo se ha probado la rama de Windows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ESPECIFICACION = RAIZ / "empaquetado" / "especificacion.json"


def plataforma_actual() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "darwin"
    return "linux"


def cargar_especificacion() -> dict:
    if not ESPECIFICACION.is_file():
        raise SystemExit(f"No se encontró la especificación: {ESPECIFICACION}")
    with open(ESPECIFICACION, encoding="utf-8") as handle:
        return json.load(handle)


def comprobar_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        raise SystemExit(
            "Falta PyInstaller. Instálalo con:\n"
            f'    "{sys.executable}" -m pip install pyinstaller\n'
            "Después vuelve a ejecutar este script."
        )


def sha256(path: Path, bloque: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            data = handle.read(bloque)
            if not data:
                break
            digest.update(data)
    return digest.hexdigest()


def tamano_carpeta(path: Path) -> int:
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            try:
                total += item.stat().st_size
            except OSError:
                pass
    return total


def _quitar_solo_lectura(carpeta: Path) -> None:
    """Windows no borra ni sobrescribe archivos con atributo de solo lectura."""
    for ruta in [carpeta, *carpeta.rglob("*")]:
        try:
            os.chmod(ruta, 0o777 if ruta.is_dir() else 0o666)
        except OSError:
            continue


def _borrar_carpeta(carpeta: Path, intentos: int = 6) -> None:
    """Borra una carpeta tolerando solo-lectura y bloqueos pasajeros."""
    for intento in range(1, intentos + 1):
        try:
            shutil.rmtree(carpeta)
            return
        except FileNotFoundError:
            return
        except OSError as exc:
            if intento == 1:
                # La causa más común en Windows: archivos copiados como solo
                # lectura (el logo de origen lo estaba).
                _quitar_solo_lectura(carpeta)
            if intento == intentos:
                raise SystemExit(
                    f"No se pudo borrar {carpeta}:\n  {exc}\n\n"
                    "Cierra la aplicación si está abierta y vuelve a intentarlo. "
                    "Si persiste, excluye la carpeta del antivirus."
                )
            time.sleep(1.5 * intento)


def limpiar(espec: dict) -> None:
    salida = RAIZ / espec["empaquetado"]["carpeta_salida"]
    trabajo = RAIZ / espec["empaquetado"]["carpeta_trabajo"]
    for carpeta in (salida, trabajo):
        if carpeta.exists():
            _borrar_carpeta(carpeta)
            print(f"  borrado {carpeta.relative_to(RAIZ)}")


def argumentos_pyinstaller(espec: dict, plataforma: str, salida: Path, trabajo: Path) -> list[str]:
    datos = espec["datos_incluidos"]
    separador = os.pathsep
    config_plataforma = espec["plataformas"][plataforma]

    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--name",
        espec["nombre"],
        "--distpath",
        str(salida),
        "--workpath",
        str(trabajo),
        "--specpath",
        str(trabajo),
        "--paths",
        str(RAIZ / "scripts"),
    ]

    if config_plataforma.get("ventana"):
        args.append("--windowed")

    icono = config_plataforma.get("icono")
    if icono and (RAIZ / icono).is_file():
        args += ["--icon", str(RAIZ / icono)]

    args += config_plataforma.get("argumentos", [])

    for item in datos:
        origen = RAIZ / item["origen"]
        if not origen.exists():
            if item.get("obligatorio"):
                raise SystemExit(f"Falta la carpeta obligatoria: {origen}")
            continue
        args += ["--add-data", f"{origen}{separador}{item['destino']}"]

    for coleccion in espec.get("colecciones", []):
        args += ["--collect-all", coleccion]
    for metadato in espec.get("metadatos", []):
        args += ["--copy-metadata", metadato]
    for oculto in espec.get("ocultos", []):
        args += ["--hidden-import", oculto]
    for excluido in espec.get("excluir", []):
        args += ["--exclude-module", excluido]

    # Módulos propios que no se importan desde el lanzador: PyInstaller debe
    # analizarlos para arrastrar sus dependencias (docx, requests, win32com…).
    for modulo in (
        "config",
        "material",
        "learn_engine",
        "aprender_module",
        "llm_provider",
        "study_outputs",
        "apa7_word",
        "init_materia",
        "convert_pdf_md",
        "convertir_epub_automatico",
    ):
        args += ["--hidden-import", modulo]

    # El propio script de Streamlit viaja como dato, no como módulo.
    args.append(str(RAIZ / espec["punto_entrada"]))
    return args


def montar_paquete(espec: dict, plataforma: str, salida: Path) -> Path:
    """Devuelve la carpeta que se entrega."""
    nombre = espec["nombre"]
    config_plataforma = espec["plataformas"][plataforma]
    formato = config_plataforma["formato"]

    if formato == "app":
        # macOS: PyInstaller deja dist/Estudio UTE.app -> se mueve a una carpeta
        bundle = salida / f"{nombre}.app"
        if not bundle.is_dir():
            raise SystemExit(f"No se generó el bundle esperado: {bundle}")
        contenedor = salida / nombre
        contenedor.mkdir(parents=True, exist_ok=True)
        destino = contenedor / bundle.name
        if destino.exists():
            shutil.rmtree(destino)
        shutil.move(str(bundle), str(destino))
    else:
        contenedor = salida / nombre
        if not contenedor.is_dir():
            raise SystemExit(f"No se generó la carpeta esperada: {contenedor}")

    # Semilla de datos (materia de ejemplo, recursos, carpetas)
    semilla = RAIZ / espec["semilla"]
    if semilla.is_dir():
        shutil.copytree(semilla, contenedor, dirs_exist_ok=True)
        # copy2 conserva el atributo de solo lectura; en el paquete se entrega
        # todo escribible para que el estudiante pueda editar sus datos.
        _quitar_solo_lectura(contenedor / "datos")
        print(f"  semilla copiada desde {semilla.relative_to(RAIZ)}")

    # Instrucciones y manifiesto
    leeme = RAIZ / espec["empaquetado"]["leeme"]
    if leeme.is_file():
        shutil.copy2(leeme, contenedor / "LEEME.md")

    ejecutable_rel = config_plataforma["ejecutable"]
    if formato == "app":
        binario = contenedor / ejecutable_rel / "Contents" / "MacOS" / nombre
    else:
        binario = contenedor / ejecutable_rel

    manifiesto = {
        "esquema": 1,
        "nombre": nombre,
        "version": espec["version"],
        "descripcion": espec["descripcion"],
        "plataforma": plataforma,
        "arquitectura": platform.machine(),
        "construido": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "python": platform.python_version(),
        "punto_entrada": ejecutable_rel,
        "carpeta_datos": "datos",
        "datos_sembrados": sorted(
            p.name for p in (contenedor / "datos" / "materias").glob("*") if p.is_dir()
        ) if (contenedor / "datos" / "materias").is_dir() else [],
        "incluye_libros": False,
        "requiere_office": "solo para exportar Word/PowerPoint",
        "verificar_con": "python empaquetado/verificar_paquete.py <carpeta>",
        "binario": {
            "ruta": str(binario.relative_to(contenedor)).replace("\\", "/"),
            "existe": binario.is_file(),
            "sha256": sha256(binario) if binario.is_file() else None,
            "bytes": binario.stat().st_size if binario.is_file() else None,
        },
        "total_archivos": sum(1 for p in contenedor.rglob("*") if p.is_file()),
        "total_bytes": tamano_carpeta(contenedor),
    }
    destino_manifiesto = contenedor / espec["empaquetado"]["manifiesto"]
    destino_manifiesto.write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  manifiesto: {destino_manifiesto.relative_to(RAIZ)}")
    return contenedor


def comprimir(espec: dict, plataforma: str, contenedor: Path, salida: Path) -> Path | None:
    nombre_zip = espec["empaquetado"]["nombre_zip"].format(
        nombre=espec["nombre"].replace(" ", "-"),
        version=espec["version"],
        plataforma=plataforma,
    )
    destino = salida / nombre_zip
    print(f"  comprimiendo {contenedor.name} (puede tardar varios minutos)…")
    if plataforma == "darwin":
        # Los .app usan enlaces simbólicos relativos; zipfile los expandiría y
        # rompería el bundle. `ditto` es la herramienta nativa que los conserva.
        resultado = subprocess.run(
            [
                "ditto",
                "-c",
                "-k",
                "--sequesterRsrc",
                "--keepParent",
                str(contenedor),
                str(destino),
            ]
        )
        if resultado.returncode != 0:
            raise SystemExit("ditto falló al comprimir el paquete de macOS.")
        return destino
    base = salida / nombre_zip[:-4]
    archivo = shutil.make_archive(str(base), "zip", root_dir=salida, base_dir=contenedor.name)
    return Path(archivo)


def main() -> int:
    parser = argparse.ArgumentParser(description="Construye el paquete portable de Estudio UTE")
    parser.add_argument("--sin-zip", action="store_true", help="no comprimir el resultado")
    parser.add_argument("--limpiar", action="store_true", help="borrar build/ y dist/ y salir")
    args = parser.parse_args()

    espec = cargar_especificacion()
    plataforma = plataforma_actual()
    salida = RAIZ / espec["empaquetado"]["carpeta_salida"]
    trabajo = RAIZ / espec["empaquetado"]["carpeta_trabajo"]

    print("=" * 62)
    print(f"  {espec['nombre']} {espec['version']} · paquete portable · {plataforma}")
    print("=" * 62)

    if args.limpiar:
        limpiar(espec)
        print("Limpieza terminada.")
        return 0

    comprobar_pyinstaller()

    print("\n[1/4] Limpiando salidas anteriores")
    limpiar(espec)

    print("\n[2/4] Ejecutando PyInstaller")
    comando = argumentos_pyinstaller(espec, plataforma, salida, trabajo)
    inicio = time.time()
    resultado = subprocess.run(comando, cwd=str(RAIZ))
    if resultado.returncode != 0:
        print("\nPyInstaller falló. Revisa el mensaje anterior.")
        return resultado.returncode
    print(f"  terminado en {time.time() - inicio:.0f} s")

    print("\n[3/4] Montando el paquete (datos, LEEME, manifiesto)")
    contenedor = montar_paquete(espec, plataforma, salida)

    archivo_zip = None
    if not args.sin_zip and espec["empaquetado"].get("crear_zip"):
        print("\n[4/4] Comprimiendo")
        archivo_zip = comprimir(espec, plataforma, contenedor, salida)
    else:
        print("\n[4/4] Sin comprimir (--sin-zip)")

    total_mb = tamano_carpeta(contenedor) / (1024 * 1024)
    print("\n" + "=" * 62)
    print(f"  Carpeta: {contenedor}")
    print(f"  Tamaño:  {total_mb:.0f} MB")
    if archivo_zip:
        print(f"  ZIP:     {archivo_zip} ({archivo_zip.stat().st_size / 1024 / 1024:.0f} MB)")
    print("=" * 62)
    print("\nPara comprobarlo antes de compartirlo:")
    print(f'    "{sys.executable}" empaquetado/verificar_paquete.py "{contenedor}"')
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    raise SystemExit(main())
