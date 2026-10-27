#!/usr/bin/env python3
"""
Aplicación Streamlit del entorno de estudio de Psicología Clínica.

Reúne la biblioteca de la materia, la generación de documentos APA 7 y el
sistema de aprendizaje. El análisis del material es local: no se inventan
contenidos que no estén en los libros importados.
"""

import streamlit as st
import os
import sys
import subprocess
import pathlib
from datetime import datetime
import json
import base64

# Añadir el directorio de scripts al path
SCRIPTS_DIR = pathlib.Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from config import (
    BASE_DIR,
    MATERIAS_DIR,
    SALIDAS_DIR,
    list_materias,
    get_materia_dir,
    ensure_dirs,
)
from material import load_material, has_text, quick_size
import study_outputs
from llm_provider import AIClient, AIConfig, AIError, PRESETS, detect_local_models

# Importar módulo de aprendizaje
from aprender_module import run_aprender

LOGO_PATH = BASE_DIR / "recursos" / "marca" / "ute_logo.jpg"
LOGO_PNG = BASE_DIR / "recursos" / "marca" / "ute_logo.png"

# Configuración de la página
st.set_page_config(
    page_title="UTE · Estudio de Psicología Clínica",
    page_icon=str(LOGO_PNG if LOGO_PNG.exists() else "🧠"),
    layout="wide",
    initial_sidebar_state="expanded",
)


def _ir_a(pagina: str) -> None:
    """Callback de navegación (se ejecuta antes de reescribir la página)."""
    st.session_state["opcion"] = pagina


def _aplicar_preset(preset: str) -> None:
    """Rellena dirección y modelo con los valores del proveedor elegido."""
    datos = PRESETS.get(preset, {})
    st.session_state["ia_base_url"] = datos.get("base_url", "")
    st.session_state["ia_modelo"] = datos.get("model", "")


def _materias_utiles() -> list[str]:
    """Materias con texto importado primero: son las que producen algo."""
    return sorted(list_materias(), key=lambda nombre: (not has_text(nombre), nombre.lower()))


OPCIONES_MENU = [
    "🏠 Inicio",
    "🎓 Aprender - Sistema Integrado",
    "📚 Crear nueva materia",
    "📖 Importar libro del facilitador (PDF → Markdown)",
    "🤖 Analizar libro (guía de estudio)",
    "✍️ Asistente de Escritura",
    "📊 Generar PowerPoint con Imagenes Reales",
    "📝 Generar trabajo en Word (APA 7ª)",
    "📊 Generar presentación en PowerPoint (APA 7ª)",
    "📈 Ver materias existentes",
    "📓 Guía de reflexión semanal",
    "📕 Convertir EPUB a Markdown",
    "⚙️ Configuración y herramientas",
]

# --- Barra lateral: identidad, navegación y estado -------------------------
with st.sidebar:
    if LOGO_PATH.exists():
        _logo_b64 = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
        st.markdown(
            f"""
            <div style="background:#ffffff;border-radius:14px;padding:14px 16px;
                        margin-bottom:14px;box-shadow:0 1px 3px rgba(0,0,0,.12);
                        text-align:center;">
                <img src="data:image/jpeg;base64,{_logo_b64}"
                     alt="Universidad UTE" style="width:100%;max-width:230px;height:auto;" />
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("#### 📋 Menú")
    opcion = st.selectbox(
        "Sección",
        OPCIONES_MENU,
        key="opcion",
        label_visibility="collapsed",
    )

    _materias_sidebar = list_materias()
    _ai_config = AIConfig.load()
    st.caption(f"{len(_materias_sidebar)} materia(s) · {_ai_config.describe()}")
    if not _ai_config.enabled:
        st.caption("La IA es opcional: todo funciona con el material local.")

st.title("🧠 Entorno de Estudio · Psicología Clínica")
st.caption(f"Universidad UTE · ruta base `{BASE_DIR}`")

def _ejecutar_en_proceso(script_path, args):
    """Ejecuta un script auxiliar dentro del propio proceso.

    En el paquete portable ``sys.executable`` es el ejecutable de la app, no un
    intérprete de Python, así que no se puede lanzar ``python script.py``. Se
    ejecuta con ``runpy`` capturando la salida, que es lo que estos scripts
    (crear materia, importar PDF, convertir EPUB) devuelven por stdout.
    """
    import contextlib
    import io
    import runpy

    buffer = io.StringIO()
    argv_original = sys.argv
    try:
        sys.argv = [str(script_path), *[str(arg) for arg in args]]
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            try:
                runpy.run_path(str(script_path), run_name="__main__")
                codigo = 0
            except SystemExit as exc:
                codigo = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
    finally:
        sys.argv = argv_original

    salida = buffer.getvalue()
    if codigo == 0:
        return True, salida
    return False, f"Error al ejecutar {script_path.name}:\n{salida}"


def run_script(script_name, *args):
    """Ejecuta un script auxiliar y devuelve (éxito, salida)."""
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        return False, f"Error: No se encontró el script {script_name}"

    if getattr(sys, "frozen", False):
        try:
            return _ejecutar_en_proceso(script_path, args)
        except Exception as e:
            return False, f"Error inesperado al ejecutar {script_name}: {e}"

    try:
        cmd = [sys.executable, str(script_path)] + list(args)
        result = subprocess.run(cmd, cwd=str(SCRIPTS_DIR), capture_output=True, text=True)

        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, f"Error al ejecutar {script_name}:\n{result.stderr}"
    except Exception as e:
        return False, f"Error inesperado: {e}"

@st.cache_data(ttl=900, show_spinner=False)
def check_office_availability():
    """Comprueba si Word y PowerPoint están registrados, sin abrirlos.

    Antes esta función lanzaba una instancia de Word y otra de PowerPoint en
    cada carga de la página (~4 s y ventanas parpadeando). El registro de COM
    responde en milisegundos y no altera nada.
    """
    try:
        import win32com.client  # noqa: F401
    except ImportError:
        return False, "pywin32 no está instalado. Instálalo con: pip install pywin32"

    import winreg

    faltan = []
    for aplicacion in ("Word.Application", "PowerPoint.Application"):
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, aplicacion + r"\CLSID"):
                pass
        except OSError:
            faltan.append(aplicacion.split(".")[0])
    if faltan:
        return False, "No se encontró en Windows: " + ", ".join(faltan) + "."
    return True, "Microsoft Office disponible (Word y PowerPoint)."


def _materia_con_material(materia_nombre):
    """Carga el material y explica por qué no sirve, si es el caso."""
    bundle = load_material(materia_nombre)
    if not bundle.has_content:
        return None, (
            "Esta materia todavía no tiene texto aprovechable. Importa el libro "
            "(PDF/EPUB → Markdown) o usa «Convertir EPUB a Markdown»."
        )
    return bundle, ""


def _guardar_en_salidas(materia_nombre, filename, contenido):
    materia_dir = get_materia_dir(materia_nombre)
    salidas = materia_dir / "salidas"
    salidas.mkdir(parents=True, exist_ok=True)
    path = salidas / filename
    path.write_text(contenido, encoding="utf-8")
    return path


def _slug(texto, limit=48):
    limpio = "".join(c if c.isalnum() or c in " -_" else " " for c in texto)
    limpio = "_".join(limpio.split())
    return limpio[:limit] or "material"


def _texto_desde_material(materia_dir, max_chars=8000):
    """Prosa real del libro para el documento de Word (con sus secciones)."""
    bundle = load_material(materia_dir.name)
    if not bundle.has_content:
        return ""
    partes: list[str] = []
    seccion_actual = None
    total = 0
    for parrafo in bundle.paragraphs:
        seccion = parrafo.heading_path[-1] if parrafo.heading_path else ""
        if seccion and seccion != seccion_actual:
            partes.append(f"\n{seccion}\n")
            seccion_actual = seccion
        partes.append(parrafo.text.replace("*", ""))
        total += len(parrafo.text)
        if total >= max_chars:
            break
    return "\n\n".join(partes)


def _grupos_por_seccion(materia_dir, max_grupos=10, max_vinetas=5, max_largo=190):
    """(título, viñetas) por sección del libro, para las diapositivas."""
    from material import split_sentences

    bundle = load_material(materia_dir.name)
    if not bundle.has_content:
        return []
    grupos: list[tuple[str, list[str]]] = []
    actual = None
    vinetas: list[str] = []
    for parrafo in bundle.paragraphs:
        seccion = parrafo.heading_path[-1] if parrafo.heading_path else ""
        if seccion and seccion != actual:
            if actual and vinetas:
                grupos.append((actual, vinetas[:max_vinetas]))
            actual = seccion
            vinetas = []
            if len(grupos) >= max_grupos:
                break
        for frase in split_sentences(parrafo.text):
            frase = " ".join(frase.replace("*", "").split())
            if 40 <= len(frase) <= max_largo:
                vinetas.append(frase)
            if len(vinetas) >= max_vinetas + 2:
                break
    if actual and vinetas and len(grupos) < max_grupos:
        grupos.append((actual, vinetas[:max_vinetas]))
    return grupos


def analizar_epub_agente(materia_nombre, tema=""):
    """Genera una guía de estudio verificable a partir del material real."""
    bundle, error = _materia_con_material(materia_nombre)
    if bundle is None:
        return f"❌ {error}"
    topic = (tema or bundle.materia).strip()
    try:
        texto, motor = study_outputs.study_guide(bundle, topic)
    except Exception as exc:  # pragma: no cover - defensivo
        return f"❌ No se pudo generar la guía: {exc}"
    path = _guardar_en_salidas(materia_nombre, f"guia_{_slug(topic)}.md", texto)
    etiqueta = "con IA" if motor == "ia" else "desde el material"
    return (
        f"✅ **Guía generada {etiqueta}**\n\n"
        f"Archivo: `{path.name}`\n\n"
        f"{texto[:2500]}"
    )


def asistente_escritura_agente(
    tema, tipo_trabajo, materia_nombre, autor="", institucion="", profesor=""
):
    """Estructura APA 7 con el material como base; sin inventar contenido."""
    bundle, error = _materia_con_material(materia_nombre)
    if bundle is None:
        return f"❌ {error}"
    try:
        texto, motor = study_outputs.writing_outline(
            bundle,
            tema,
            tipo_trabajo,
            autor=autor,
            institucion=institucion,
            profesor=profesor,
        )
    except Exception as exc:  # pragma: no cover - defensivo
        return f"❌ No se pudo generar la estructura: {exc}"
    path = _guardar_en_salidas(materia_nombre, f"{_slug(tema)}_estructura.md", texto)
    etiqueta = "con IA" if motor == "ia" else "desde el material"
    return (
        f"✅ **Estructura generada {etiqueta}**\n\n"
        f"Archivo: `{path.name}`\n\n"
        f"{texto[:2500]}"
    )


def generar_powerpoint_imagenes_agente(
    materia_nombre, trabajo_name, titulo, n_slides=12
):
    """Estructura de diapositivas con contenido real del material."""
    bundle, error = _materia_con_material(materia_nombre)
    if bundle is None:
        return f"❌ {error}"
    try:
        texto, motor = study_outputs.slides_outline(
            bundle, titulo, materia=materia_nombre, n_slides=int(n_slides)
        )
    except Exception as exc:  # pragma: no cover - defensivo
        return f"❌ No se pudo generar la estructura: {exc}"
    path = _guardar_en_salidas(
        materia_nombre, f"{trabajo_name}_estructura_ppt.md", texto
    )
    etiqueta = "con IA" if motor == "ia" else "desde el material"
    return (
        f"✅ **Estructura de PowerPoint generada {etiqueta}**\n\n"
        f"Archivo: `{path.name}`\n\n"
        f"{texto[:2500]}"
    )


def generate_word_with_office(materia_dir, trabajo_name, titulo):
    """Genera un documento Word usando automatización de Office"""
    try:
        import win32com.client
        import pythoncom

        # Inicializar COM para este hilo
        pythoncom.CoInitialize()

        # Crear instancia de Word
        word = win32com.client.Dispatch("Word.Application")
        try:
            # Intentar ocultar Word (operación en segundo plano)
            word.Visible = False
        except Exception as visible_error:
            # Si no se puede ocultar (política de seguridad de Office), continuar visible
            # Esto puede ocurrir en algunas configuraciones de Office
            word.Visible = True
            # Nota: Word será visible durante la generacion, pero se cerrará al finalizar

        # Crear nuevo documento
        doc = word.Documents.Add()

        # Configurar estilos APA 7 (simplificado)
        # En una implementación completa, se configurarían estilos específicos

        # Portada
        titulo_range = doc.Range(0, 0)
        titulo_range.InsertAfter(titulo.upper() + '\n\n')
        titulo_range.Font.Name = "Times New Roman"
        titulo_range.Font.Size = 12
        titulo_range.Font.Bold = True
        titulo_range.ParagraphFormat.Alignment = 1  # Centrado
        titulo_range.ParagraphFormat.LineSpacing = 2.0

        # Autor, institución, etc. (datos de ejemplo)
        autor = "Tu Nombre"
        institucion = "Nombre de tu Universidad"
        curso = materia_dir.name.replace('_', ' ')
        profesor = "Nombre del Profesor"
        fecha = datetime.now().strftime("%B %d, %Y")

        # Agregar información de portada
        for texto in [autor, institucion, curso, profesor, fecha]:
            p_range = doc.Range(doc.Content.End - 1, doc.Content.End - 1)
            p_range.InsertAfter(texto + '\n\n')
            p_range.Font.Name = "Times New Roman"
            p_range.Font.Size = 12
            p_range.ParagraphFormat.Alignment = 1  # Centrado
            p_range.ParagraphFormat.LineSpacing = 2.0

        # Salto de página
        doc.Range(doc.Content.End - 1, doc.Content.End - 1).InsertBreak(7)  # wdPageBreak

        # Contenido: primero el libro real; si no hay, las notas de la materia.
        contenido_libro = _texto_desde_material(materia_dir)
        if contenido_libro:
            full_content = "Contenido del material\n\n" + contenido_libro
        else:
            content_parts = []
            memory_file = materia_dir / "memory.md"
            if memory_file.exists():
                content_parts.append(memory_file.read_text(encoding="utf-8"))
            fuentes_file = materia_dir / "fuentes_usadas.md"
            if fuentes_file.exists():
                content_parts.append(
                    "\n\n## Fuentes Consultadas\n\n"
                    + fuentes_file.read_text(encoding="utf-8")
                )
            libro_file = materia_dir / "libro_principal.md"
            if libro_file.exists():
                content_parts.append(
                    "\n\n## Contenido del Libro Principal\n\n"
                    + libro_file.read_text(encoding="utf-8")
                )
            full_content = (
                "\n\n".join(content_parts)
                if content_parts
                else "# Contenido\n\nEscribe aquí tu trabajo..."
            )

        # Insertar contenido
        content_range = doc.Range(doc.Content.End - 1, doc.Content.End - 1)
        content_range.InsertAfter(full_content)

        # Guardar documento
        output_dir = materia_dir / "salidas"
        output_dir.mkdir(exist_ok=True)
        safe_title = "".join(c for c in titulo if c.isalnum() or c in " _-").rstrip()
        filename = output_dir / f"{trabajo_name}_{safe_title}.docx"

        doc.SaveAs(str(filename))
        doc.Close()
        word.Quit()

        pythoncom.CoUninitialize()

        return True, f"Documento Word generado: {filename}"

    except Exception as e:
        try:
            if 'word' in locals():
                word.Quit()
        except:
            pass
        try:
            pythoncom.CoUninitialize()
        except:
            pass
        return False, f"Error al generar Word con Office: {e}"

def generate_powerpoint_with_office(materia_dir, trabajo_name, titulo):
    """Genera una presentación PowerPoint usando automatización de Office"""
    try:
        import win32com.client
        import pythoncom

        # Inicializar COM para este hilo
        pythoncom.CoInitialize()

        # Crear instancia de PowerPoint
        powerpoint = win32com.client.Dispatch("PowerPoint.Application")
        try:
            # Intentar ocultar PowerPoint (operación en segundo plano)
            powerpoint.Visible = False
        except Exception as visible_error:
            # Si no se puede ocultar (política de seguridad de Office), continuar visible
            # Esto es normal en algunas configuraciones de Office LTSC
            powerpoint.Visible = True
            # Nota: PowerPoint será visible durante la generacion, pero se cerrará al finalizar

        # Crear nueva presentación
        presentation = powerpoint.Presentations.Add()

        # Diapositiva de título
        title_slide = presentation.Slides.Add(1, 1)  # ppLayoutTitle
        title_slide.Shapes.Title.TextFrame.TextRange.Text = titulo.upper()
        title_slide.Shapes.Placeholders(2).TextFrame.TextRange.Text = "Tu Nombre\nNombre de tu Universidad\nNombre del Curso\nNombre del Profesor\n" + datetime.now().strftime("%B %d, %Y")

        # Una diapositiva por sección del libro, con viñetas reales.
        grupos = _grupos_por_seccion(materia_dir)
        if grupos:
            for titulo_seccion, vinetas in grupos:
                slide = presentation.Slides.Add(
                    presentation.Slides.Count + 1, 2
                )  # ppLayoutText
                slide.Shapes.Title.TextFrame.TextRange.Text = titulo_seccion[:80]
                text_range = slide.Shapes.Placeholders(2).TextFrame.TextRange
                for vineta in vinetas:
                    text_range.InsertAfter(vineta + "\n")
        else:
            # Sin libro importado: se usan las notas de la materia.
            content_parts = []
            memory_file = materia_dir / "memory.md"
            if memory_file.exists():
                content_parts.append(memory_file.read_text(encoding="utf-8"))
            fuentes_file = materia_dir / "fuentes_usadas.md"
            if fuentes_file.exists():
                content_parts.append(
                    "\n\n## Fuentes Consultadas\n\n"
                    + fuentes_file.read_text(encoding="utf-8")
                )
            libro_file = materia_dir / "libro_principal.md"
            if libro_file.exists():
                content_parts.append(
                    "\n\n## Contenido del Libro Principal\n\n"
                    + libro_file.read_text(encoding="utf-8")
                )
            full_content = (
                "\n\n".join(content_parts)
                if content_parts
                else "# Contenido\n\nEscribe aquí tu trabajo..."
            )
            lines = full_content.split("\n")
            bullet_points = []
            current_point = ""
            for line in lines:
                line = line.strip()
                if line and not line.startswith("#"):
                    if line.startswith("- ") or line.startswith("* "):
                        bullet_points.append(line[2:])
                    elif line[0].isdigit() and ". " in line[:5]:
                        bullet_points.append(line[line.find(". ") + 2:])
                    else:
                        if current_point:
                            bullet_points.append(current_point)
                        current_point = line
                elif line.startswith("#"):
                    if current_point:
                        bullet_points.append(current_point)
                        current_point = ""
            if current_point:
                bullet_points.append(current_point)

            for i in range(0, len(bullet_points), 5):
                slide = presentation.Slides.Add(
                    presentation.Slides.Count + 1, 2
                )  # ppLayoutText
                slide.Shapes.Title.TextFrame.TextRange.Text = (
                    f"Contenido - Parte {i // 5 + 1}"
                )
                text_range = slide.Shapes.Placeholders(2).TextFrame.TextRange
                for j in range(i, min(i + 5, len(bullet_points))):
                    text_range.InsertAfter(bullet_points[j] + "\n")

        # Diapositiva de referencias (sólo fuentes reales del material)
        ref_slide = presentation.Slides.Add(presentation.Slides.Count + 1, 2)  # ppLayoutText
        ref_slide.Shapes.Title.TextFrame.TextRange.Text = "Referencias"
        _bundle_ref = load_material(materia_dir.name)
        _fuentes_reales = [
            pathlib.Path(ruta).stem.replace("_", " ")
            for ruta, _tipo, caracteres in _bundle_ref.sources
            if caracteres > 2000
        ]
        if _fuentes_reales:
            ref_text = "\n".join(
                f"{nombre}. (s. f.). [Material de estudio de {materia_dir.name}]."
                for nombre in _fuentes_reales[:6]
            )
        else:
            ref_text = (
                "Pendiente: importa el libro de la materia para generar las "
                "referencias reales."
            )
        ref_slide.Shapes.Placeholders(2).TextFrame.TextRange.Text = ref_text

        # Guardar presentación
        output_dir = materia_dir / "salidas"
        output_dir.mkdir(exist_ok=True)
        safe_title = "".join(c for c in titulo if c.isalnum() or c in " _-").rstrip()
        filename = output_dir / f"{trabajo_name}_{safe_title}.pptx"

        presentation.SaveAs(str(filename))
        presentation.Close()
        powerpoint.Quit()

        pythoncom.CoUninitialize()

        return True, f"Presentación PowerPoint generada: {filename}"

    except Exception as e:
        try:
            if 'powerpoint' in locals():
                powerpoint.Quit()
        except:
            pass
        try:
            pythoncom.CoUninitialize()
        except:
            pass
        return False, f"Error al generar PowerPoint con Office: {e}"

# Página de inicio
if opcion == "🏠 Inicio":
    st.header("Bienvenido al Entorno de Estudio")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Estado del sistema")
        materias = list_materias()
        st.metric("Materias configuradas", len(materias))

        office_available, office_msg = check_office_availability()
        if office_available:
            st.success("✅ Microsoft Office disponible")
        else:
            st.warning(f"⚠️ {office_msg}")

        _config_inicio = AIConfig.load()
        _cliente_inicio = AIClient(_config_inicio)
        if _cliente_inicio.available:
            st.success(f"🧠 IA activa: {_config_inicio.describe()}")
        else:
            st.info("📖 Motor local: todo se genera con el material, sin IA externa.")

        if materias:
            _con_material = sum(1 for nombre in materias if has_text(nombre))
            st.caption(f"{_con_material} de {len(materias)} materias con texto importado.")

        st.info(f"📁 Ruta base: {BASE_DIR}")

    with col2:
        st.subheader("🚀 Accesos rápidos")
        st.button(
            "🎓 Aprender",
            width="stretch",
            on_click=_ir_a,
            args=("🎓 Aprender - Sistema Integrado",),
        )
        st.button(
            "📚 Crear nueva materia",
            width="stretch",
            on_click=_ir_a,
            args=("📚 Crear nueva materia",),
        )
        st.button(
            "📖 Importar libro (PDF → Markdown)",
            width="stretch",
            on_click=_ir_a,
            args=("📖 Importar libro del facilitador (PDF → Markdown)",),
        )
        st.button(
            "🤖 Analizar libro y sacar guía",
            width="stretch",
            on_click=_ir_a,
            args=("🤖 Analizar libro (guía de estudio)",),
        )
        st.button(
            "📝 Generar trabajo en Word",
            width="stretch",
            on_click=_ir_a,
            args=("📝 Generar trabajo en Word (APA 7ª)",),
        )
        st.button(
            "📊 Generar presentación en PowerPoint",
            width="stretch",
            on_click=_ir_a,
            args=("📊 Generar presentación en PowerPoint (APA 7ª)",),
        )

# Página para crear nueva materia
elif opcion == "📚 Crear nueva materia":
    st.header("📚 Crear Nueva Materia")

    materia_name = st.text_input(
        "Nombre de la materia:",
        placeholder="Ejemplo: Metodologia Cuantitativa",
        key="nueva_materia_nombre",
    )
    if st.button("Crear materia", type="primary", key="crear_materia_btn") and materia_name:
        materia_dir = get_materia_dir(materia_name)
        if materia_dir.exists():
            st.error(f"La materia '{materia_name}' ya existe en: {materia_dir}")
        else:
            success, message = run_script("init_materia.py", materia_name)
            if success:
                st.success(f"✅ Materia '{materia_name}' creada exitosamente!")
                st.info(f"📁 Carpeta creada: {materia_dir}")
                with st.expander("Ver archivos creados"):
                    st.write(
                        """
                        - guia_aprendizaje.md
                        - libro_principal.md
                        - memory.md
                        - fuentes_usadas.md
                        - salidas/ (directorio)
                        """
                    )
            else:
                st.error(f"❌ Error al crear la materia: {message}")

# Página para importar libro
elif opcion == "📖 Importar libro del facilitador (PDF → Markdown)":
    st.header("📖 Importar Libro del Facilitador")

    materias = list_materias()

    # Seleccionar o crear materia
    if materias:
        materia_options = ["Crear nueva materia"] + materias
        materia_choice = st.selectbox("Seleccione materia:", materia_options)

        if materia_choice == "Crear nueva materia":
            materia_name = st.text_input("Nombre de la nueva materia:", key="new_materia_import")
        else:
            materia_name = materia_choice
    else:
        st.info("No hay materias existentes. Debe crear una primero.")
        materia_name = st.text_input("Nombre de la nueva materia:", key="new_materia_import")

    # Ruta del PDF
    pdf_path = st.text_input(
        "Ruta completa al archivo PDF:",
        placeholder="C:\\ruta\\al\\libro.pdf",
        help="Arrastre y suelte el archivo aquí o escriba la ruta completa"
    )

    if st.button("Importar Libro", type="primary"):
        if not materia_name:
            st.error("Debe especificar un nombre de materia.")
        elif not pdf_path:
            st.error("Debe especificar la ruta del archivo PDF.")
        else:
            pdf_file = pathlib.Path(pdf_path.strip('"'))
            if not pdf_file.exists():
                st.error(f"El archivo no existe: {pdf_file}")
            else:
                success, message = run_script("convert_pdf_md.py", str(pdf_file), materia_name)
                if success:
                    st.success(f"✅ Libro importado para materia '{materia_name}'!")
                    st.info(f"📁 Revisa: {get_materia_dir(materia_name)}")

                    with st.expander("Próximos pasos"):
                        st.write("""
                        1. Ve a la carpeta de la materia
                        2. Convierte el PDF a Markdown con pandoc:
                           ```bash
                           pandoc "nombre_del_libro.pdf" -o libro_principal.md
                           ```
                        3. Reemplaza el contenido del placeholder con el resultado.
                        4. La IA ahora usará principalmente ese libro para responder preguntas.
                        """)
                else:
                    st.error(f"❌ Error al importar el libro: {message}")

# Página para generar trabajo en Word
elif opcion == "📝 Generar trabajo en Word (APA 7ª)":
    st.header("📝 Generar Trabajo en Word (APA 7ª Edición)")

    materias = list_materias()
    if not materias:
        st.error("No hay materias existentes. Cree una primero.")
    else:
        materia_name = st.selectbox("Seleccione materia:", materias)

        if materia_name:
            materia_dir = get_materia_dir(materia_name)

            col1, col2 = st.columns(2)

            with col1:
                trabajo_name = st.text_input(
                    "Nombre interno del trabajo:",
                    placeholder="ej. trabajo1, parcial, tarea",
                    value="trabajo1"
                )

            with col2:
                titulo = st.text_input(
                    "Título completo del trabajo:",
                    placeholder="Ejemplo: Efectos de la terapia cognitivo-conductual en la ansiedad"
                )

            # Opción para usar automatización de Office
            use_office = st.checkbox(
                "Usar automatización de Microsoft Office (recomendado para mejor formato)",
                value=True,
                help="Requiere que Microsoft Office esté instalado y pywin32 disponible"
            )

            if st.button("Generar Trabajo", type="primary"):
                if not trabajo_name:
                    trabajo_name = "trabajo1"

                if not titulo:
                    st.error("El título es requerido.")
                else:
                    with st.spinner("Generando documento Word..."):
                        if use_office:
                            success, message = generate_word_with_office(materia_dir, trabajo_name, titulo)
                        else:
                            success, message = run_script("apa7_word.py", str(materia_dir), trabajo_name, titulo)

                    if success:
                        st.success(f"✅ {message}")

                        # Mostrar archivo generado
                        salida_dir = materia_dir / "salidas"
                        if salida_dir.exists():
                            docs = list(salida_dir.glob("*.docx"))
                            if docs:
                                latest_doc = docs[-1]
                                st.info(f"📄 Último documento: {latest_doc.name}")

                                # Botón para descargar (en entorno real)
                                with open(latest_doc, "rb") as file:
                                    st.download_button(
                                        label="💾 Descargar documento",
                                        data=file.read(),
                                        file_name=latest_doc.name,
                                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                                    )
                    else:
                        st.error(f"❌ {message}")

# Página para generar presentación en PowerPoint
elif opcion == "📊 Generar presentación en PowerPoint (APA 7ª)":
    st.header("📊 Generar Presentación en PowerPoint (APA 7ª Edición)")

    materias = list_materias()
    if not materias:
        st.error("No hay materias existentes. Cree una primero.")
    else:
        materia_name = st.selectbox("Seleccione materia:", materias, key="ppt_materia")

        if materia_name:
            materia_dir = get_materia_dir(materia_name)

            col1, col2 = st.columns(2)

            with col1:
                trabajo_name = st.text_input(
                    "Nombre interno de la presentación:",
                    placeholder="ej. presentacion1, seminario, exposicion",
                    value="presentacion1",
                    key="ppt_trabajo"
                )

            with col2:
                titulo = st.text_input(
                    "Título completo de la presentación:",
                    placeholder="Ejemplo: Principios de la terapia dialectico-conductual",
                    key="ppt_titulo"
                )

            # Información sobre requerimientos
            st.info("""
            💡 **Requisitos para generacion de PowerPoint:**
            - Microsoft PowerPoint debe estar instalado
            - Se requiere la librería `pywin32` (`pip install pywin32`)
            - La presentación se generará con formato básico APA 7
            """)

            if st.button("Generar Presentación", type="primary", key="gen_ppt"):
                if not trabajo_name:
                    trabajo_name = "presentacion1"

                if not titulo:
                    st.error("El título es requerido.")
                else:
                    with st.spinner("Generando presentación PowerPoint..."):
                        success, message = generate_powerpoint_with_office(materia_dir, trabajo_name, titulo)

                    if success:
                        st.success(f"✅ {message}")

                        # Mostrar archivo generado
                        salida_dir = materia_dir / "salidas"
                        if salida_dir.exists():
                            ppts = list(salida_dir.glob("*.pptx"))
                            if ppts:
                                latest_ppt = ppts[-1]
                                st.info(f"📊 Última presentación: {latest_ppt.name}")

                                # Botón para descargar (en entorno real)
                                with open(latest_ppt, "rb") as file:
                                    st.download_button(
                                        label="💾 Descargar presentación",
                                        data=file.read(),
                                        file_name=latest_ppt.name,
                                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                                    )
                    else:
                        st.error(f"❌ {message}")

# Página para analizar el libro y sacar una guía de estudio
elif opcion == "🤖 Analizar libro (guía de estudio)":
    st.header("🤖 Analizar libro y sacar guía de estudio")

    materias = _materias_utiles()
    if not materias:
        st.warning("No hay materias creadas. Primero crea una materia.")
    else:
        st.markdown(
            "La guía se construye con el texto del libro: conceptos, definiciones, "
            "afirmaciones universales y preguntas. Cada elemento indica su fuente."
        )
        col1, col2 = st.columns([1, 1])
        with col1:
            materia_seleccionada = st.selectbox(
                "Materia:", materias, key="analizar_materia"
            )
        with col2:
            tema = st.text_input(
                "Tema o capítulo (opcional):",
                placeholder="En blanco = todo el material",
                key="analizar_tema",
            )

        _bundle_analisis = load_material(materia_seleccionada)
        _nivel, _detalle = _bundle_analisis.quality()
        st.caption(f"Material: **{_nivel}** — {_detalle}")
        _hay_ia, _motor = study_outputs.ai_status()
        st.caption(f"Motor de redacción: {_motor}")

        if st.button("🔍 Generar guía de estudio", type="primary", key="analizar_epub"):
            with st.spinner("Leyendo el material y armando la guía..."):
                resultado = analizar_epub_agente(materia_seleccionada, tema)
            if resultado.startswith("✅"):
                st.success("Guía generada.")
                st.markdown(resultado)
                _salida = get_materia_dir(materia_seleccionada) / "salidas"
                _guias = sorted(
                    _salida.glob("guia_*.md"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                ) if _salida.is_dir() else []
                if _guias:
                    with open(_guias[0], "rb") as f:
                        st.download_button(
                            "⬇️ Descargar guía (.md)",
                            data=f.read(),
                            file_name=_guias[0].name,
                            mime="text/markdown",
                        )
            else:
                st.error(resultado)

# Página para asistente de escritura
elif opcion == "✍️ Asistente de Escritura":
    st.header("✍️ Asistente de Escritura (APA 7ª)")

    materias = _materias_utiles()
    if not materias:
        st.warning("No hay materias creadas. Primero crea una materia.")
    else:
        st.markdown(
            "Genera la **estructura** del trabajo con el material como base. "
            "Lo que va entre corchetes lo escribes tú: la herramienta no redacta "
            "tu trabajo por ti."
        )
        col1, col2 = st.columns(2)
        with col1:
            materia_seleccionada = st.selectbox(
                "Materia:", materias, key="escritura_materia"
            )
            tema = st.text_input(
                "Tema del trabajo:",
                placeholder="Ej: Terapia cognitivo-conductual para la ansiedad",
                key="escritura_tema",
            )
            tipo_trabajo = st.selectbox(
                "Tipo de trabajo:",
                [
                    "Ensayo",
                    "Trabajo de investigación",
                    "Reflexión",
                    "Análisis de caso",
                    "Revisión teórica",
                ],
                key="tipo_trabajo",
            )
        with col2:
            autor = st.text_input("Tu nombre:", key="escritura_autor")
            institucion = st.text_input(
                "Institución:", value="Universidad UTE", key="escritura_institucion"
            )
            profesor = st.text_input("Docente:", key="escritura_profesor")

        _hay_ia, _motor = study_outputs.ai_status()
        st.caption(f"Motor de redacción: {_motor}")

        if st.button("Generar estructura", type="primary", key="escritura_generar"):
            if not tema.strip():
                st.error("El tema es obligatorio.")
            else:
                with st.spinner("Armando la estructura APA 7..."):
                    resultado = asistente_escritura_agente(
                        tema, tipo_trabajo, materia_seleccionada,
                        autor, institucion, profesor,
                    )
                if resultado.startswith("✅"):
                    st.success("Estructura generada.")
                    st.markdown(resultado)
                    _salida = get_materia_dir(materia_seleccionada) / "salidas"
                    _docs = sorted(
                        _salida.glob("*_estructura.md"),
                        key=lambda p: p.stat().st_mtime,
                        reverse=True,
                    ) if _salida.is_dir() else []
                    if _docs:
                        with open(_docs[0], "rb") as f:
                            st.download_button(
                                "⬇️ Descargar estructura (.md)",
                                data=f.read(),
                                file_name=_docs[0].name,
                                mime="text/markdown",
                            )
                else:
                    st.error(resultado)

# Página para generar estructura de PowerPoint
elif opcion == "📊 Generar PowerPoint con Imagenes Reales":
    st.header("📊 Generar PowerPoint con imágenes del material")

    materias = _materias_utiles()
    if not materias:
        st.warning("No hay materias creadas. Primero crea una materia.")
    else:
        st.markdown(
            "Arma la estructura de diapositivas con contenido real del libro: una "
            "idea por diapositiva, cita del material y notas del ponente. Las "
            "imágenes deben salir del propio libro; si no hay figura, no se inventa."
        )
        col1, col2 = st.columns(2)
        with col1:
            materia_seleccionada = st.selectbox(
                "Materia:", materias, key="ppt_materia_imagenes"
            )
            titulo = st.text_input(
                "Título de la presentación:",
                placeholder="Ej: Fundamentos de la Terapia Cognitivo-Conductual",
                key="ppt_titulo_imagenes",
            )
        with col2:
            trabajo_name = st.text_input(
                "Nombre del archivo:",
                value="presentacion",
                key="ppt_archivo_imagenes",
            )
            num_diapositivas = st.slider(
                "Número aproximado de diapositivas:",
                min_value=8,
                max_value=20,
                value=12,
                step=1,
                key="ppt_num_imagenes",
            )

        _hay_ia, _motor = study_outputs.ai_status()
        st.caption(f"Motor de redacción: {_motor}")

        if st.button("Generar estructura", type="primary", key="ppt_generar_imagenes"):
            if not titulo.strip():
                st.error("El título es obligatorio.")
            else:
                with st.spinner("Armando la estructura de diapositivas..."):
                    resultado = generar_powerpoint_imagenes_agente(
                        materia_seleccionada, trabajo_name, titulo, num_diapositivas
                    )
                if resultado.startswith("✅"):
                    st.success("Estructura generada.")
                    st.markdown(resultado)
                    _materia_dir = get_materia_dir(materia_seleccionada)
                    _archivo = _materia_dir / "salidas" / f"{trabajo_name}_estructura_ppt.md"
                    if _archivo.exists():
                        with open(_archivo, "rb") as f:
                            st.download_button(
                                "⬇️ Descargar estructura (.md)",
                                data=f.read(),
                                file_name=_archivo.name,
                                mime="text/markdown",
                            )
                else:
                    st.error(resultado)

# Página para Aprender - Sistema Integrado
elif opcion == "🎓 Aprender - Sistema Integrado":
    run_aprender()

elif opcion == "📕 Convertir EPUB a Markdown":
    st.header("📕 Convertir EPUB a Markdown")
    
    materias = list_materias()
    
    if not materias:
        st.warning("No hay materias creadas. Primero cree una materia usando el menú principal.")
    else:
        # Mostrar información sobre el conversor
        st.info("""
        💡 **Conversor EPUB → Markdown**
        Este script busca archivos .epub en las carpetas de materias y los convierte a formato Markdown usando pandoc.
        Los archivos convertidos se guardan en la subcarpeta "salidas/" de cada materia.
        """)
        
        # Botón para ejecutar el conversor
        if st.button("🔄 Ejecutar Conversor Automático EPUB → Markdown", type="primary"):
            with st.spinner("Buscando archivos EPUB y convirtiendo a Markdown..."):
                try:
                    # Ejecutar el script de conversión con el flag --overwrite para evitar problemas en entornos no interactivos
                    success, message = run_script("convertir_epub_automatico.py", "--overwrite")
                    
                    if success:
                        st.success("✅ Conversión completada exitosamente!")
                        
                        # Mostrar el mensaje de salida
                        with st.expander("Ver detalles de la conversión"):
                            st.text(message)
                        
                        # Mostrar archivos generados
                        st.subheader("📁 Archivos generados")
                        for materia_name in materias:
                            salidas_dir = SALIDAS_DIR / materia_name
                            if salidas_dir.exists():
                                md_files = list(salidas_dir.glob("*.md"))
                                if md_files:
                                    st.write(f"**{materia_name}:** {len(md_files)} archivo(s) Markdown")
                                    for md_file in md_files:
                                        # Mostrar información básica del archivo
                                        file_size = md_file.stat().st_size
                                        st.caption(f"  • {md_file.name} ({file_size:,} bytes)")
                    else:
                        st.error(f"❌ Error al ejecutar el conversor:")
                        st.error(message)
                        
                except Exception as e:
                    st.error(f"❌ Error inesperado: {e}")

# Página para ver materias existentes
elif opcion == "📈 Ver materias existentes":
    st.header("📈 Materias Existentes")

    materias = list_materias()
    if not materias:
        st.info("No hay materias creadas todavía.")
        st.button(
            "Crear primera materia",
            on_click=_ir_a,
            args=("📚 Crear nueva materia",),
        )
    else:
        for i, materia in enumerate(materias, 1):
            with st.expander(f"{i}. 📚 {materia}"):
                materia_dir = get_materia_dir(materia)
                st.write(f"📁 **Carpeta:** `{materia_dir}`")

                _archivos, _caracteres = quick_size(materia)
                st.caption(
                    f"Material en disco: {_archivos} archivo(s) · "
                    f"{_caracteres:,} caracteres".replace(",", ".")
                )

                # Contar archivos
                col1, col2, col3, col4 = st.columns(4)

                guia = materia_dir / "guia_aprendizaje.md"
                libro = materia_dir / "libro_principal.md"
                memory = materia_dir / "memory.md"
                fuentes = materia_dir / "fuentes_usadas.md"
                salidas_dir = materia_dir / "salidas"

                with col1:
                    st.metric("Guía", "✅" if guia.exists() else "❌")
                    st.metric("Libro", "✅" if libro.exists() else "❌")

                with col2:
                    st.metric("Memory", "✅" if memory.exists() else "❌")
                    st.metric("Fuentes", "✅" if fuentes.exists() else "❌")

                with col3:
                    if salidas_dir.exists():
                        doc_count = len(list(salidas_dir.glob("*.docx")))
                        ppt_count = len(list(salidas_dir.glob("*.pptx")))
                        st.metric("Word", doc_count)
                        st.metric("PowerPoint", ppt_count)
                    else:
                        st.metric("Word", "0")
                        st.metric("PowerPoint", "0")

                with col4:
                    if st.button(f"Abrir carpeta", key=f"open_{i}"):
                        st.info(f"Carpeta: {materia_dir}")

                    if st.button(f"Ver detalles", key=f"details_{i}"):
                        # Mostrar contenido de los archivos
                        tabs = st.tabs(["Guía", "Libro", "Memory", "Fuentes"])

                        with tabs[0]:
                            if guia.exists():
                                st.text_area("Guía de Aprendizaje", guia.read_text(encoding="utf-8"), height=200, disabled=True)
                            else:
                                st.info("Archivo no existe")

                        with tabs[1]:
                            if libro.exists():
                                st.text_area("Libro Principal", libro.read_text(encoding="utf-8"), height=200, disabled=True)
                            else:
                                st.info("Archivo no existe")

                        with tabs[2]:
                            if memory.exists():
                                st.text_area("Memory", memory.read_text(encoding="utf-8"), height=200, disabled=True)
                            else:
                                st.info("Archivo no existe")

                        with tabs[3]:
                            if fuentes.exists():
                                st.text_area("Fuentes Usadas", fuentes.read_text(encoding="utf-8"), height=200, disabled=True)
                            else:
                                st.info("Archivo no existe")

# Página para guía de reflexión semanal
elif opcion == "📓 Guía de reflexión semanal":
    st.header("📓 Guía de Reflexión Semanal")
    st.info("""
    Esta sección le ayudará a crear y seguir una guía de reflexión semanal para cada materia,
    tal como describió en su solicitud inicial.
    """)

    materias = list_materias()
    if not materias:
        st.warning("No hay materias existentes. Cree una primera.")
    else:
        materia_name = st.selectbox("Seleccione materia para guía de reflexión:", materias, key="reflexion_materia")

        if materia_name:
            materia_dir = get_materia_dir(materia_name)
            reflexion_file = materia_dir / "reflexion_semanal.md"

            st.subheader(f"Guía de reflexión para: {materia_name}")

            # Cargar o crear guía de reflexión
            if reflexion_file.exists():
                contenido_actual = reflexion_file.read_text(encoding="utf-8")
            else:
                contenido_actual = """# Guía de Reflexión Semanal

## Semana 1
- [ ] Tarea 1: Describir
- [ ] Tarea 2: Analizar
- [ ] Tarea 3: Aplicar
- [ ] Tarea 4: Crear presentación PowerPoint
- [ ] Tarea 5: Subir trabajo a plataforma universitaria

## Semana 2
- [ ] Tarea 1: Describir
- [ ] Tarea 2: Analizar
- [ ] Tarea 3: Aplicar
- [ ] Tarea 4: Crear presentación PowerPoint
- [ ] Tarea 5: Subir trabajo a plataforma universitaria

*Use esta plantilla para planificar sus actividades semanales.*
"""

            # Editor de la guía
            nuevo_contenido = st.text_area(
                "Edite su guía de reflexión semanal:",
                value=contenido_actual,
                height=400,
                help="Use sintaxis markdown. Puede usar casillas de verificación [- ] para tareas."
            )

            col1, col2 = st.columns(2)

            with col1:
                if st.button("💾 Guardar Guía de Reflexión", type="primary"):
                    reflexion_file.write_text(nuevo_contenido, encoding="utf-8")
                    st.success("✅ Guía de reflexión guardada exitosamente!")

            with col2:
                if st.button("👁️ Vista previa"):
                    st.markdown(nuevo_contenido)

            # Mostrar vista previa automática
            with st.expander("Vista previa automática"):
                st.markdown(nuevo_contenido)

elif opcion == "⚙️ Configuración y herramientas":
    st.header("⚙️ Configuración y Herramientas")

    tab_ia, tab1, tab2, tab3, tab4 = st.tabs(
        [
            "🧠 Motor de IA",
            "🔧 Estado del Sistema",
            "📦 Instalación de Dependencias",
            "💡 Ideas de Mejora",
            "📋 Automatización Avanzada",
        ]
    )

    with tab_ia:
        st.subheader("🧠 Motor de IA (opcional)")
        st.markdown(
            "La aplicación funciona completa sin IA: las preguntas y las guías se "
            "construyen con el texto del material. Si conectas un modelo, se usa "
            "**sólo** para redactar la explicación del profesor; las respuestas "
            "siguen verificándose contra el libro.\n\n"
            "Compatible con cualquier servicio que hable la API de OpenAI "
            "(DeepSeek, OpenAI, Ollama, LM Studio…). La clave se guarda en "
            "`recursos/ia_config.json`, en tu equipo."
        )
        _cfg = AIConfig.load()
        _presets = list(PRESETS)
        _idx = _presets.index(_cfg.preset) if _cfg.preset in _presets else 0

        col_a, col_b = st.columns([1, 2])
        with col_a:
            _preset = st.selectbox(
                "Proveedor",
                _presets,
                index=_idx,
                format_func=lambda key: PRESETS[key]["label"],
                key="ia_preset",
            )
        with col_b:
            st.write("")
            st.write("")
            st.button(
                "Rellenar con los valores del proveedor",
                on_click=_aplicar_preset,
                args=(_preset,),
            )

        _base = st.text_input(
            "Dirección (base URL)",
            value=_cfg.base_url,
            placeholder="https://api.deepseek.com/v1",
            key="ia_base_url",
        )
        _modelo = st.text_input(
            "Modelo",
            value=_cfg.model,
            placeholder="deepseek-chat",
            key="ia_modelo",
        )
        _clave = st.text_input(
            "Clave de API",
            value=_cfg.api_key,
            type="password",
            help="Se guarda sólo en este equipo. Déjala vacía en modelos locales.",
            key="ia_clave",
        )
        _activa = st.toggle("Usar IA cuando esté disponible", value=_cfg.enabled, key="ia_activa")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Guardar", type="primary", key="ia_guardar"):
                _nueva = AIConfig(
                    enabled=_activa,
                    preset=_preset,
                    base_url=_base.strip(),
                    model=_modelo.strip(),
                    api_key=_clave,
                )
                _nueva.save()
                st.success("Configuración guardada.")
                st.rerun()
        with col2:
            if st.button("Probar conexión", key="ia_probar"):
                _prueba = AIClient(
                    AIConfig(
                        enabled=True,
                        preset=_preset,
                        base_url=_base.strip(),
                        model=_modelo.strip(),
                        api_key=_clave,
                    )
                )
                _ok, _msg = _prueba.status()
                (st.success if _ok else st.error)(_msg)
        with col3:
            if st.button("Buscar modelos locales", key="ia_detectar"):
                _locales = detect_local_models()
                if _locales:
                    _encontrado = _locales[0]
                    st.session_state["ia_base_url"] = _encontrado.base_url
                    st.session_state["ia_modelo"] = _encontrado.model
                    st.success(
                        f"Encontrado {_encontrado.describe()}. Pulsa Guardar para usarlo."
                    )
                else:
                    st.info("No se detectó Ollama ni LM Studio en este equipo.")

        st.caption(f"Estado actual: {_cfg.describe()} · clave {_cfg.masked_key()}")
        if _cfg.enabled:
            _ok, _msg = AIClient(_cfg).status()
            (st.success if _ok else st.warning)(_msg)

    with tab1:
        st.subheader("Estado del Sistema")

        # Verificar dependencias
        dependencias = {
            "streamlit": "streamlit",
            "python-docx": "docx",
            "python-pptx": "pptx",
            "pypdf": "pypdf",
            "pywin32": "win32com.client",
        }

        for dep_name, import_name in dependencias.items():
            try:
                __import__(import_name)
                st.success(f"✅ {dep_name}")
            except ImportError:
                st.error(f"❌ {dep_name} - No instalado")

        # Verificar Office
        office_available, office_msg = check_office_availability()
        if office_available:
            st.success("✅ Microsoft Office disponible")
        else:
            st.error(f"❌ Microsoft Office: {office_msg}")

        # Estadísticas de uso
        materias = list_materias()
        total_trabajos = 0
        total_presentaciones = 0

        for materia in materias:
            materia_dir = get_materia_dir(materia)
            salidas_dir = materia_dir / "salidas"
            if salidas_dir.exists():
                total_trabajos += len(list(salidas_dir.glob("*.docx")))
                total_presentaciones += len(list(salidas_dir.glob("*.pptx")))

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Materias", len(materias))
        with col2:
            st.metric("Trabajos Word", total_trabajos)
        with col3:
            st.metric("Presentaciones PowerPoint", total_presentaciones)

    with tab2:
        st.subheader("Instalación de Dependencias")
        st.code("""
# Dependencias de la aplicación
pip install streamlit python-docx python-pptx pypdf PyYAML requests

# Automatización de Microsoft Office en Windows
pip install pywin32

# Conversión PDF/EPUB → Markdown (recomendado)
# winget install pandoc
# o descarga desde https://pandoc.org/installing.html
        """, language="bash")

        if st.button("Verificar instalación de pandoc"):
            try:
                result = subprocess.run(["pandoc", "--version"], capture_output=True, text=True)
                if result.returncode == 0:
                    st.success(f"✅ Pandoc disponible: {result.stdout.split()[0]}")
                else:
                    st.error("❌ Pandoc no encontrado o error al ejecutarlo")
            except FileNotFoundError:
                st.error("❌ Pandoc no está instalado. Use: winget install pandoc o visite https://pandoc.org")
            except Exception as e:
                st.error(f"❌ Error al verificar pandoc: {e}")

    with tab3:
        st.subheader("💡 Ideas de Mejora y Nuevas Funcionalidades")

        ideas = [
            {
                "titulo": "🔍 Búsqueda inteligente de referencias",
                "descripcion": "Integrar búsquedas en bases académicas (Google Scholar, PubMed, PsycINFO) para encontrar referencias automáticamente y generar citas en formato APA 7.",
                "beneficio": "Ahorra tiempo en investigación y garantiza referencias actualizadas y relevantes."
            },
            {
                "titulo": "📊 Seguimiento de tareas y progreso",
                "descripcion": "Sistema de gestión de tareas integrado con calendario y recordatorios para seguir el progreso de cada materia y entregas universitarias.",
                "beneficio": "Mejor organización y cumplimiento de fechas límite académicas."
            },
            {
                "titulo": "🤖 Asistente de escritura académica",
                "descripcion": "IA especializada que ayuda a mejorar la claridad, coherencia y estilo académico siguiendo normas APA 7, con detección de plagio básica.",
                "beneficio": "Mejora la calidad de los trabajos académicos y reduce tiempo de revisión."
            },
            {
                "titulo": "🔄 Generación automática de presentaciones",
                "descripcion": "Crear presentaciones PowerPoint automáticamente a partir del contenido escrito en memory.md o fuentes_usadas.md.",
                "beneficio": "Ahorra tiempo en preparación de exposiciones y seminarios."
            },
            {
                "titulo": "📱 Notificaciones y recordatorios",
                "descripcion": "Sistema de notificaciones para entregas próximas, revisiones de memoria semanal y actualizaciones de materias.",
                "beneficio": "Mantiene al estudiante al tanto de sus responsabilidades académicas."
            },
            {
                "titulo": "💾 Copia de seguridad y sincronización",
                "descripcion": "Integración con servicios de almacenamiento en la nube (OneDrive, Google Drive) para respaldo automático y acceso desde múltiples dispositivos.",
                "beneficio": "Previene pérdida de trabajo y permite acceso desde cualquier lugar."
            },
            {
                "titulo": "📈 Analítica de aprendizaje",
                "descripcion": "Métricas de tiempo de estudio, temas revisados, patrones de aprendizaje y sugerencias personalizadas.",
                "beneficio": "Optimiza el tiempo de estudio y identifica áreas que necesitan más atención."
            },
            {
                "titulo": "🎯 Planificador de estudios personalizado",
                "descripcion": "Crea planes de estudio adaptativos basado en el calendario académico, dificultad de materias y objetivos de aprendizaje.",
                "beneficio": "Maximiza la eficiencia del tiempo de estudio según necesidades individuales."
            }
        ]

        for idea in ideas:
            with st.expander(idea["titulo"]):
                st.write(idea["descripcion"])
                st.caption(f"💡 **Beneficio:** {idea['beneficio']}")

    with tab4:
        st.subheader("📋 Automatización Avanzada")
        st.info("""
        Ideas para automatizar completamente el flujo de trabajo académico:
        """)

        automatizacion_ideas = [
            "🔄 **Flujo completo**: PDF → Markdown → Análisis IA → Borrador Word/PowerPoint → Revisión → Entrega",
            "📅 **Programador de tareas**: Automatizar recordatorios según el calendario universitario",
            "📧 **Integración con plataforma**: Subida automática de trabajos a plataformas como Moodle, Canvas, Blackboard",
            "📚 **Gestor de bibliografía**: Creación y gestión automática de bibliotecas de referencias en formato APA 7",
            "🎨 **Plantillas inteligentes**: Plantillas Word/PowerPoint que se adaptan automáticamente al contenido y normas APA",
            "👁️‍🗨️ **Revisor de contenido**: IA que revisa coherencia, fluidez, claridad y sugiere mejoras",
            "📊 **Dashboard académico**: Vista completa de progreso, entregas pendientes y rendimiento por materia",
            "🤖 **Asistente 24/7**: Chatbot especializado en la materia que responde preguntas basado en los materiales de estudio"
        ]

        for idea in automatizacion_ideas:
            st.write(idea)

# Pie de página
st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
st.markdown(
    """
    <div style="border-top:1px solid rgba(128,128,128,.28); margin-top:1rem;
                padding-top:1rem; text-align:center; color:#8b8b8b;
                font-size:.86rem; line-height:1.7;">
        <span>Hecho con amor ❤️ por Gregorio Valdez,
        estudiante de Psicología Clínica</span>
        <div style="font-size:.76rem; opacity:.75; margin-top:.35rem;">
            Universidad UTE · Entorno de Estudio
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
