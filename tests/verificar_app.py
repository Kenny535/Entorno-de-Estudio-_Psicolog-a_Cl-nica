#!/usr/bin/env python3
"""
Verificación de la aplicación (sin abrir el navegador).

Comprueba tres capas:
  1. Lectura del material (limpieza de Markdown, definiciones, secciones).
  2. Motor de aprendizaje (preguntas, sondeo, plan).
  3. Interfaz Streamlit con AppTest (todas las páginas y el flujo de Aprender).

Uso:
    python tests\\verificar_app.py

Sale con código 0 si todo pasa y 1 si algo falla.
"""

from __future__ import annotations

import pathlib
import sys
import traceback

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = RAIZ / "scripts"
sys.path.insert(0, str(SCRIPTS))

APP = SCRIPTS / "streamlit_app.py"
MATERIA = "Teoria_de_la_Personalidad"

fallos: list[str] = []
pasos: list[str] = []


def check(nombre: str, condicion: bool, detalle: str = "") -> None:
    if condicion:
        pasos.append(nombre)
        print(f"  ok   {nombre}")
    else:
        fallos.append(f"{nombre} {detalle}".strip())
        print(f"  FALLA {nombre} {detalle}")


# ---------------------------------------------------------------------------
# 1. Material
# ---------------------------------------------------------------------------

def test_material() -> None:
    print("\n[1] Lectura del material")
    import material

    crudo = "## [*Resumen*]{.calibre2}\n\n[Texto de\nprueba]{.calibre3}\n\n[]{#x}\n"
    limpio = material.clean_markdown(crudo)
    check("quita atributos de calibre", "{.calibre" not in limpio, limpio)
    check("quita anclas vacías", "[]{#" not in limpio)

    frases = material.split_sentences(
        "El Dr. Smith llegó. La personalidad es estable. ¿Se puede medir?"
    )
    check("separa frases sin cortar abreviaturas", len(frases) == 3, str(frases))

    bundle = material.load_material(MATERIA)
    check("el libro real tiene texto", bundle.has_content)
    check("detecta definiciones", len(bundle.definitions) > 10, str(len(bundle.definitions)))
    check("detecta secciones", len(bundle.sections) > 50, str(len(bundle.sections)))
    check(
        "las secciones empiezan en un capítulo real",
        bool(bundle.sections)
        and material._fold(bundle.sections[0].title).startswith("capitulo"),
        bundle.sections[0].title if bundle.sections else "sin secciones",
    )
    check(
        "no lee sus propias salidas como material",
        all("estructura" not in p.source and "guia_" not in p.source for p in bundle.paragraphs),
    )


# ---------------------------------------------------------------------------
# 2. Motor
# ---------------------------------------------------------------------------

def test_motor() -> None:
    print("\n[2] Motor de aprendizaje")
    import material
    import learn_engine as le

    bundle = material.load_material(MATERIA)
    factory = le.QuestionFactory(bundle)
    meta = "Entender los rasgos de personalidad"
    strands = le.choose_strands(bundle, factory, meta)
    check("elige hilos para la meta", len(strands) >= 1, str(strands))

    problemas = []
    total = 0
    for definition in factory.definitions[:12]:
        for difficulty in range(1, 6):
            question = factory.get(definition.term, difficulty)
            if question is None:
                continue
            total += 1
            if len(set(question.options)) != len(question.options):
                problemas.append(f"opciones repetidas en {definition.term}/{difficulty}")
            if len(question.options) < 3:
                problemas.append(f"menos de 3 opciones en {definition.term}/{difficulty}")
            if not 0 <= question.correct < len(question.options):
                problemas.append(f"índice inválido en {definition.term}/{difficulty}")
            if not question.explanation.strip():
                problemas.append(f"sin explicación en {definition.term}/{difficulty}")
            if not question.source:
                problemas.append(f"sin fuente en {definition.term}/{difficulty}")
            if question.difficulty != difficulty:
                problemas.append(f"dificultad desalineada en {definition.term}/{difficulty}")
            # La explicación no puede contener la marca de la opción correcta
            # antes de responder (no debe filtrarse la respuesta en el enunciado).
            if question.correct_text in question.prompt:
                problemas.append(f"respuesta visible en el enunciado {definition.term}/{difficulty}")
    check("todas las preguntas son respondibles", not problemas, "; ".join(problemas[:3]))
    check("genera preguntas de varios niveles", total >= 20, str(total))

    q1 = factory.get("personalidad", 3)
    q2 = factory.get("personalidad", 3)
    check(
        "las preguntas son estables entre ejecuciones",
        q1 is not None and q2 is not None and q1.options == q2.options and q1.correct == q2.correct,
    )

    plan = le.build_plan(bundle, factory, meta, strands)
    check("el plan tiene nodos", len(plan.nodes) >= 3, str(len(plan.nodes)))
    check("el plan tiene raíz", any(n.kind == "unconditional" for n in plan.nodes))
    check("el plan termina en la meta", plan.nodes[-1].kind == "goal")
    check("el mapa Mermaid se genera", plan.mermaid.startswith("graph TD"))

    teacher = le.Teacher(bundle, plan, factory)
    textos = [teacher.step(node) for node in plan.nodes]
    check("cada nodo tiene motivación", all(t.motivate.strip() for t in textos))
    check("cada nodo tiene conexión", all(t.connect.strip() for t in textos))

    strand = strands[0]
    nivel = strand.next_difficulty
    check("el sondeo empieza en un nivel válido", nivel in strand.levels, str(nivel))
    question = factory.get(strand.concept, nivel)
    if question is not None:
        strand.record(le.ProbeAnswer(
            concept=strand.concept, difficulty=nivel, question_key=question.key,
            prompt=question.prompt, correct=True, chosen=question.correct_text,
            expected=question.correct_text,
        ))
    check("el sondeo avanza tras un acierto", strand.next_difficulty != nivel or strand.bracketed)

    session = le.LearningSession(materia=MATERIA, goal=meta, plan=plan, strands=strands)
    md = session.to_markdown()
    check("la sesión se serializa a Markdown", "# Sesión de aprendizaje" in md and "mermaid" in md)


# ---------------------------------------------------------------------------
# 3. Interfaz
# ---------------------------------------------------------------------------

PAGINAS = [
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


def test_interfaz() -> None:
    print("\n[3] Interfaz Streamlit")
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP), default_timeout=300)
    at.run()
    check("la aplicación arranca", not at.exception,
          str(at.exception[0].value) if at.exception else "")

    for pagina in PAGINAS:
        at.sidebar.selectbox[0].select(pagina)
        at.run()
        detalle = str(at.exception[0].value).splitlines()[0] if at.exception else ""
        check(f"página: {pagina}", not at.exception, detalle)

    # Navegación por accesos rápidos
    at.sidebar.selectbox[0].select("🏠 Inicio")
    at.run()
    accesos = [b for b in at.button if "Aprender" in b.label]
    if accesos:
        accesos[0].click()
        at.run()
        check(
            "los accesos rápidos cambian de página",
            at.sidebar.selectbox[0].value.startswith("🎓 Aprender"),
            at.sidebar.selectbox[0].value,
        )


def test_flujo_aprender() -> None:
    print("\n[4] Flujo completo de Aprender")
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP), default_timeout=300)
    at.run()
    at.sidebar.selectbox[0].select("🎓 Aprender - Sistema Integrado")
    at.run()
    check("la sección Aprender abre", not at.exception)

    at.selectbox[0].select(MATERIA)
    at.text_input[0].input("Entender los rasgos de personalidad")
    at.run()
    boton = [b for b in at.button if b.label == "Empezar"][0]
    boton.click()
    at.run()
    check("la sesión se crea", "ap_session" in at.session_state)

    for _ in range(40):
        labels = [b.label for b in at.button]
        if "Comprobar" in labels:
            radios = [r for r in at.radio if r.label == "Elige una opción:"]
            if radios:
                radios[0].set_value(0)
                at.run()
            next(b for b in at.button if b.label == "Comprobar").click()
            at.run()
            continue
        if "Siguiente pregunta →" in labels:
            next(b for b in at.button if b.label == "Siguiente pregunta →").click()
            at.run()
            continue
        if "Construir el plan →" in labels:
            next(b for b in at.button if b.label == "Construir el plan →").click()
            at.run()
            continue
        if "Aprobar plan y empezar la lección" in labels:
            next(b for b in at.button if b.label == "Aprobar plan y empezar la lección").click()
            at.run()
            continue
        if "Continuar →" in labels:
            next(b for b in at.button if b.label == "Continuar →").click()
            at.run()
            continue
        if "Seguir y marcarlo para repasar" in labels:
            next(b for b in at.button if b.label == "Seguir y marcarlo para repasar").click()
            at.run()
            continue
        if "💾 Guardar sesión" in labels:
            next(b for b in at.button if b.label == "💾 Guardar sesión").click()
            at.run()
            break
        break

    session = at.session_state.get("ap_session")
    check("el flujo llega al cierre", session is not None and session.phase == "cierre",
          getattr(session, "phase", "sin sesión"))
    check("no hubo excepciones en el flujo", not at.exception,
          str(at.exception[0].value) if at.exception else "")
    guardada = at.session_state.get("ap_saved")
    check("la sesión se guarda en disco", bool(guardada) and pathlib.Path(guardada).exists(),
          str(guardada))


def limpiar_artefactos() -> None:
    """Borra lo que generan las pruebas para no dejar basura en el proyecto."""
    print("\n[5] Limpieza de artefactos de prueba")
    patrones = ["guia_*.md", "*_estructura.md", "*_estructura_ppt.md"]
    borrados = 0
    for materia in (RAIZ / "materias").iterdir() if (RAIZ / "materias").is_dir() else []:
        salidas = materia / "salidas"
        if not salidas.is_dir():
            continue
        for patron in patrones:
            for path in salidas.glob(patron):
                try:
                    path.unlink()
                    borrados += 1
                except OSError:
                    pass
    for path in (RAIZ / "aprendizaje_sesiones").glob("*.md"):
        try:
            path.unlink()
            borrados += 1
        except OSError:
            pass
    print(f"  {borrados} archivo(s) de prueba eliminados")


def main() -> int:
    for nombre, funcion in [
        ("material", test_material),
        ("motor", test_motor),
        ("interfaz", test_interfaz),
        ("flujo", test_flujo_aprender),
    ]:
        try:
            funcion()
        except Exception:
            traceback.print_exc()
            fallos.append(f"{nombre}: excepción inesperada")

    limpiar_artefactos()

    print("\n" + "=" * 60)
    print(f"{len(pasos)} comprobaciones correctas, {len(fallos)} fallo(s)")
    for fallo in fallos:
        print("  · " + fallo)
    print("=" * 60)
    return 0 if not fallos else 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    raise SystemExit(main())
