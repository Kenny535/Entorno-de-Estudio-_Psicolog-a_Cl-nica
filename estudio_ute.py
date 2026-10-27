#!/usr/bin/env python3
"""
Arranque del paquete portable «Estudio UTE».

Este archivo es el punto de entrada que PyInstaller convierte en ejecutable.
Hace cuatro cosas y ninguna más:

1. Prepara la carpeta de datos (``datos/`` junto al ejecutable).
2. Busca un puerto libre en 127.0.0.1.
3. Lanza Streamlit apuntando a ``scripts/streamlit_app.py``.
4. Abre el navegador.

Si algo falla antes de arrancar, deja el motivo en ``datos/registro.txt`` y
muestra un aviso del sistema: nadie tiene que abrir una consola para enterarse.

Variables de entorno útiles (para pruebas o usos avanzados):
    ESTUDIO_BASE_DIR    carpeta de datos alternativa
    ESTUDIO_PORT        puerto fijo en vez de buscar uno libre
    ESTUDIO_NO_BROWSER  si vale 1, no abre el navegador
"""

from __future__ import annotations

import os
import pathlib
import socket
import subprocess
import sys
import threading
import time
import traceback
import webbrowser

NOMBRE = "Estudio UTE"
PUERTO_INICIAL = 8501
INTENTOS_PUERTO = 25


def _raiz_recursos() -> pathlib.Path:
    """Dónde están los archivos empaquetados (scripts, recursos)."""
    if getattr(sys, "_MEIPASS", None):
        return pathlib.Path(sys._MEIPASS)
    return pathlib.Path(__file__).resolve().parent


def _log_path() -> pathlib.Path:
    base = os.environ.get("ESTUDIO_BASE_DIR", "").strip()
    if base:
        return pathlib.Path(base) / "registro.txt"
    try:
        from config import BASE_DIR  # importación tardía: ya resuelve el modo

        return pathlib.Path(BASE_DIR) / "registro.txt"
    except Exception:
        return pathlib.Path.home() / "EstudioUTE-registro.txt"


def _log(message: str) -> None:
    try:
        path = _log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    except OSError:
        pass


def _normalizar_salidas() -> None:
    """En modo ventana no hay stdout: Streamlit necesita uno escribible."""
    if sys.stdout is not None and sys.stderr is not None:
        return
    try:
        path = _log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        stream = open(path, "a", encoding="utf-8", buffering=1)
    except OSError:
        stream = open(os.devnull, "w", encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = stream
    if sys.stderr is None:
        sys.stderr = stream


def _avisar(titulo: str, mensaje: str) -> None:
    """Muestra el error sin consola (Windows/macOS) y lo registra."""
    _log(f"{titulo}: {mensaje}")
    if os.name == "nt":
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(0, mensaje, titulo, 0x10)
            return
        except Exception:
            pass
    elif sys.platform == "darwin":
        try:
            texto = mensaje.replace("\\", "\\\\").replace('"', '\\"')
            subprocess.run(
                ["osascript", "-e", f'display alert "{titulo}" message "{texto}" as critical'],
                check=False,
                timeout=30,
            )
            return
        except Exception:
            pass
    print(f"{titulo}\n{mensaje}", file=sys.stderr or sys.stdout)


def _puerto_libre(preferido: int | None = None) -> int:
    if preferido:
        return preferido
    for puerto in range(PUERTO_INICIAL, PUERTO_INICIAL + INTENTOS_PUERTO):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", puerto))
            except OSError:
                continue
            return puerto
    raise RuntimeError(
        "No hay ningún puerto libre entre "
        f"{PUERTO_INICIAL} y {PUERTO_INICIAL + INTENTOS_PUERTO - 1}."
    )


def _abrir_navegador(url: str, puerto: int, limite: float = 90.0) -> None:
    """Abre el navegador sólo cuando el servidor ya acepta conexiones.

    En un equipo lento (o con antivirus) Streamlit tarda en estar listo; abrir
    antes deja al usuario en una página de «no se puede conectar» que no sabe
    interpretar.
    """
    if os.environ.get("ESTUDIO_NO_BROWSER") == "1":
        return

    def abrir() -> None:
        inicio = time.time()
        while time.time() - inicio < limite:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.5)
                try:
                    sock.connect(("127.0.0.1", puerto))
                    break
                except OSError:
                    time.sleep(0.4)
        time.sleep(0.5)
        try:
            webbrowser.open(url)
        except Exception:
            _log(f"No se pudo abrir el navegador para {url}")

    threading.Thread(target=abrir, daemon=True).start()


def main() -> int:
    _normalizar_salidas()
    _log(f"Arranque de {NOMBRE} (congelado={getattr(sys, 'frozen', False)})")

    try:
        from config import BASE_DIR, ensure_dirs

        ensure_dirs()
        _log(f"Carpeta de datos: {BASE_DIR}")
    except Exception as exc:
        _avisar(
            NOMBRE,
            "No se pudo preparar la carpeta de datos.\n\n"
            f"Detalle: {exc}\n\nRevisa los permisos de la carpeta donde "
            "descomprimiste la aplicación.",
        )
        return 1

    app = _raiz_recursos() / "scripts" / "streamlit_app.py"
    if not app.is_file():
        _avisar(
            NOMBRE,
            "Falta el archivo de la aplicación:\n"
            f"{app}\n\n"
            "El paquete está incompleto: vuelve a descomprimir el ZIP entero, "
            "sin mover archivos sueltos.",
        )
        return 1

    try:
        puerto = _puerto_libre(int(os.environ["ESTUDIO_PORT"]) if os.environ.get("ESTUDIO_PORT") else None)
    except (RuntimeError, ValueError) as exc:
        _avisar(NOMBRE, f"No se pudo abrir un puerto local.\n\n{exc}")
        return 1

    url = f"http://127.0.0.1:{puerto}"
    _log(f"URL: {url}")

    # Streamlit no debe abrir su propia pestaña ni pedir correo.
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
    os.environ.setdefault("STREAMLIT_SERVER_HEADLESS", "true")
    os.environ.setdefault("STREAMLIT_SERVER_FILE_WATCHER_TYPE", "none")
    os.environ.setdefault("STREAMLIT_GLOBAL_DEVELOPMENT_MODE", "false")

    _abrir_navegador(url, puerto)

    sys.argv = [
        "streamlit",
        "run",
        str(app),
        "--server.address",
        "127.0.0.1",
        "--server.port",
        str(puerto),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]

    try:
        from streamlit.web import cli as stcli

        return int(stcli.main() or 0)
    except SystemExit as exc:
        return int(exc.code or 0) if isinstance(exc.code, int) else 0
    except Exception:
        detalle = traceback.format_exc()
        _log(detalle)
        _avisar(
            NOMBRE,
            "La aplicación se cerró por un error inesperado.\n\n"
            f"Detalle guardado en:\n{_log_path()}",
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
