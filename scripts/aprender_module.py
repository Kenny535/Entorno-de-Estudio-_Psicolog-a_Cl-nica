#!/usr/bin/env python3
"""
Sección «Aprender» de la aplicación.

Sigue el sistema de amosblomqvist/learn: dos principios y tres fases.

    Fase 1 · Sondear  — preguntas adaptativas que buscan el borde del
                        conocimiento, más la meta declarada por el estudiante.
    Fase 2 · Planear  — mapa de dependencias (DAG) antes de enseñar nada.
    Fase 3 · Enseñar  — por cada nodo: motivar → establecer → conectar →
                        comprobar. No se avanza con un nodo sin comprobarlo.

El texto y las preguntas salen del material real de la materia. La IA (opcional)
sólo añade la narración del profesor; las preguntas siguen ancladas al texto.
"""

from __future__ import annotations

import pathlib
import sys

import streamlit as st

SCRIPTS_DIR = pathlib.Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from config import BASE_DIR, list_materias
from material import MaterialBundle, format_sources, has_text, load_material
import learn_engine as le
from llm_provider import (
    AIClient,
    AIConfig,
    AIError,
    build_planner_messages,
    build_teacher_messages,
)

APRENDIZAJE_DIR = BASE_DIR / "aprendizaje_sesiones"
APRENDIZAJE_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Ejemplo guiado (el «cómo se ve» del sistema, tal como lo describe el repo)
# ---------------------------------------------------------------------------

DEMO_EXAMPLE = """\
### Ejemplo del método: por qué se mantiene la ansiedad

**Principio i — la raíz.** *Toda conducta que se repite está siendo reforzada
de alguna manera.* No admite matices: si algo se repite, algo lo mantiene. Se
acepta tal cual y ya tenemos suelo.

**Principio ii — el paso que podrías haber descubierto tú.** Si la evitación se
repite, algo la refuerza. ¿Qué refuerza evitar? El alivio inmediato de no sentir
miedo. De ahí: *la evitación se mantiene porque el alivio llega antes que
cualquier prueba de que el peligro no era real.*

**Conectar.** La raíz dice «lo que se repite se refuerza»; la idea nueva dice
*qué* refuerza a la evitación. Sin la raíz, el paso nuevo sería un dato suelto.

**Comprobación (opciones construidas en paralelo, sin justificaciones):**

> ¿Qué mantiene la conducta de evitación según este razonamiento?
> - El alivio que llega al evitar
> - La genética de la persona
> - La falta de información sobre el tema
> - El paso del tiempo

La correcta es la primera; la explicación va *después* de responder, no dentro
de la opción. Así el acierto no se puede adivinar por la forma del texto.
"""


# ---------------------------------------------------------------------------
# Utilidades de estado
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def _bundle_for(materia: str, stamp: str) -> MaterialBundle:
    """El material se cachea por materia y por fecha de modificación."""
    return load_material(materia)


@st.cache_resource(show_spinner=False)
def _factory_for(materia: str, stamp: str) -> le.QuestionFactory:
    return le.QuestionFactory(_bundle_for(materia, stamp))


def _stamp(materia: str) -> str:
    bundle = load_material(materia)
    return str(hash(tuple(bundle.sources)) + len(bundle.paragraphs))


def _get_context(materia: str) -> tuple[MaterialBundle, le.QuestionFactory]:
    stamp = _stamp(materia)
    return _bundle_for(materia, stamp), _factory_for(materia, stamp)


def _ai_client() -> AIClient:
    return AIClient(AIConfig.load())


def _ai_badge(session: "le.LearningSession | None") -> None:
    config = AIConfig.load()
    client = AIClient(config)
    if session and session.ai_mode == "ia" and client.available:
        st.caption(f"🧠 Narración con IA · {config.describe()}")
    else:
        st.caption(
            "📖 Modo local: el texto y las preguntas salen del material, sin IA externa."
        )


def _materias_con_texto_primero() -> list[str]:
    """Las materias con libro importado van primero: son las que se pueden usar."""
    return sorted(list_materias(), key=lambda nombre: (not has_text(nombre), nombre.lower()))


# ---------------------------------------------------------------------------
# Componente de pregunta con retroalimentación inmediata
# ---------------------------------------------------------------------------

def ask_question(question: le.Question, prefix: str) -> dict | None:
    """Muestra una pregunta y devuelve {'ok': bool, 'choice': int} al responder.

    No avanza ni recarga por su cuenta: la pantalla que la contiene decide qué
    hacer con el resultado. La explicación sólo aparece después de responder.
    """
    nonce_key = f"{prefix}:{question.key}:nonce"
    nonce = st.session_state.get(nonce_key, 0)
    base = f"{prefix}:{question.key}:{nonce}"
    state_key = f"{base}:result"
    answered = st.session_state.get(state_key)

    if answered is None:
        choice = st.radio(
            "Elige una opción:",
            options=list(range(len(question.options))),
            format_func=lambda index: question.options[index],
            index=None,
            key=f"{base}:choice",
        )
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button(
                "Comprobar",
                key=f"{base}:check",
                type="primary",
                disabled=choice is None,
            ):
                st.session_state[state_key] = {
                    "ok": choice == question.correct,
                    "choice": choice,
                }
                st.rerun()
        with col2:
            st.caption(
                f"Nivel {question.difficulty}/5 · {le.DIFFICULTY_LABELS[question.difficulty]}"
            )
        return None

    ok = bool(answered["ok"])
    if ok:
        st.success("✅ Correcto.")
    else:
        st.error(f"❌ No era esa. La respuesta es: **{question.correct_text}**")
    st.info(f"**Por qué:** {question.explanation}")
    return answered


def clear_question(question: le.Question, prefix: str) -> None:
    """Reinicia la pregunta cambiando su nonce (sin tocar claves de widgets)."""
    nonce_key = f"{prefix}:{question.key}:nonce"
    st.session_state[nonce_key] = st.session_state.get(nonce_key, 0) + 1


# ---------------------------------------------------------------------------
# Fase 0 · Configuración de la sesión
# ---------------------------------------------------------------------------

def _render_setup() -> None:
    st.subheader("Nueva sesión")
    st.markdown(
        "Elige la materia, escribe **qué quieres entender** y el sistema sondea "
        "tu nivel antes de enseñar nada."
    )
    materias = _materias_con_texto_primero()
    if not materias:
        st.warning("Todavía no hay materias. Crea una en «Crear nueva materia».")
        return

    col1, col2 = st.columns([1, 2])
    with col1:
        materia = st.selectbox("Materia", materias, key="ap_materia_sel")
    with col2:
        meta = st.text_input(
            "¿Qué quieres entender?",
            placeholder="Ej: cómo se forman los rasgos de personalidad",
            key="ap_meta_input",
        )
    modo = st.radio(
        "Motor",
        ["Auto (usa IA si está configurada)", "Sólo material local"],
        horizontal=True,
        key="ap_modo_input",
    )

    bundle_preview, _ = _get_context(materia)
    level, message = bundle_preview.quality()
    st.caption(f"Material disponible: **{level}** — {message}")

    if not st.button("Empezar", type="primary", key="ap_start"):
        return
    if not meta.strip():
        st.error("Escribe qué quieres entender.")
        return

    bundle, factory = _get_context(materia)
    if not bundle.has_content:
        st.error(
            "Esta materia no tiene texto aprovechable todavía. "
            "Importa el libro (PDF/EPUB → Markdown) o usa «Convertir EPUB a Markdown»."
        )
        st.info(message)
        return

    session = le.LearningSession(materia=materia, goal=meta.strip())
    session.strands = le.choose_strands(bundle, factory, session.goal)
    if not session.strands:
        st.error(
            "No se encontraron conceptos con material suficiente para sondearte. "
            "Prueba con otra formulación de la meta o revisa el libro."
        )
        return

    client = _ai_client()
    if modo.startswith("Auto") and client.available:
        session.ai_mode = "ia"
        session.note("Motor de IA disponible; se usará para narrar la lección.")
    else:
        session.ai_mode = "local"
        session.note("Sesión en modo local (sin IA externa).")

    session.phase = "sondeo"
    session.note(f"Meta: {session.goal}")
    session.note(f"Hilos a sondear: {', '.join(s.concept for s in session.strands)}")
    st.session_state["ap_session"] = session
    st.session_state["ap_bundle"] = bundle
    st.session_state["ap_factory"] = factory
    st.rerun()


# ---------------------------------------------------------------------------
# Fase 1 · Sondeo
# ---------------------------------------------------------------------------

def _pending_strand(session: le.LearningSession) -> "le.Strand | None":
    for strand in session.strands:
        if not strand.bracketed and strand.next_difficulty is not None:
            return strand
    return None


def _render_probe(session: le.LearningSession, factory: le.QuestionFactory) -> None:
    st.subheader("Paso 1 · Sondeo de tu nivel")
    st.markdown(
        "No es un examen: es un mapa. Se sube de dificultad mientras aciertas y se "
        "afina en cuanto algo se rompe, para encontrar el borde exacto."
    )
    st.markdown(session.probe_summary())
    st.divider()

    strand = _pending_strand(session)
    if strand is None:
        st.success("Sondeo completo: ya sabemos dónde está el borde.")
        if st.button("Construir el plan →", type="primary"):
            session.phase = "plan"
            st.rerun()
        return

    target = strand.next_difficulty
    question = factory.get(strand.concept, target)
    if question is None:
        # El nivel no tiene pregunta posible: se cierra por arriba y se sigue.
        strand.ceiling = min(strand.ceiling, target)
        st.rerun()
        return

    st.markdown(f"**Hilo:** {strand.concept}")
    st.progress(
        min(1.0, len(strand.answers) / max(len(strand.levels), 1)),
        text=f"{len(strand.answers)} respuesta(s) en este hilo",
    )
    st.markdown(f"#### {question.prompt}")
    result = ask_question(question, "probe")
    if result is None:
        return

    recorded_key = f"probe:recorded:{question.key}"
    if not st.session_state.get(recorded_key):
        answer = le.ProbeAnswer(
            concept=strand.concept,
            difficulty=target,
            question_key=question.key,
            prompt=question.prompt,
            correct=bool(result["ok"]),
            chosen=question.options[result["choice"]],
            expected=question.correct_text,
        )
        strand.record(answer)
        st.session_state[recorded_key] = True
        session.note(
            f"Sondeo · {strand.concept} · nivel {target}: "
            + ("acierto" if answer.correct else "fallo")
        )
    if st.button("Siguiente pregunta →", type="primary", key=f"probe_next:{question.key}"):
        st.rerun()


# ---------------------------------------------------------------------------
# Fase 2 · Plan
# ---------------------------------------------------------------------------

def _ai_plan(
    session: le.LearningSession,
    bundle: MaterialBundle,
    factory: le.QuestionFactory,
) -> "le.Plan | None":
    client = _ai_client()
    if session.ai_mode != "ia" or not client.available:
        return None
    excerpts = "\n\n".join(
        f"[{pathlib.Path(p.source).name}] {p.text[:600]}"
        for p in bundle.related(session.goal, limit=5)
    )
    truths = [t.text for t in bundle.truths[:6]]
    try:
        data = client.chat_json(build_planner_messages(
            session.materia, session.goal, excerpts, truths
        ))
    except AIError as exc:
        st.warning(f"La IA no pudo proponer el plan ({exc}). Se usa el plan del material.")
        return None

    nodes: list[le.TeachNode] = []
    labels: dict[str, str] = {}
    for index, root in enumerate(data.get("roots", [])[:2]):
        label = str(root.get("label", "")).strip()
        if not label:
            continue
        node_id = f"raiz{index + 1}"
        labels[label.lower()] = node_id
        nodes.append(le.TeachNode(
            id=node_id,
            label=label,
            kind="unconditional",
            statement=str(root.get("statement", label)),
            quote=str(root.get("quote", "")),
            source="material",
            section="",
            concept=label,
        ))
    for index, item in enumerate(data.get("nodes", [])[:5]):
        label = str(item.get("label", "")).strip()
        if not label:
            continue
        depends = str(item.get("depends_on", "")).strip().lower()
        parent = labels.get(depends, nodes[0].id if nodes else None)
        node_id = f"nodo{index + 1}"
        labels[label.lower()] = node_id
        nodes.append(le.TeachNode(
            id=node_id,
            label=label,
            kind="derived",
            statement=str(item.get("statement", label)),
            quote=str(item.get("quote", "")),
            source="material",
            section="",
            parent=parent,
            concept=label,
        ))
    if len(nodes) < 3:
        return None
    goal_label = str(data.get("goal") or session.goal).strip()
    nodes.append(le.TeachNode(
        id="meta",
        label=goal_label,
        kind="goal",
        statement=session.goal,
        quote="",
        source="",
        section="",
        parents=[node.id for node in nodes],
        concept=nodes[0].concept,
    ))
    return le.Plan(
        goal=session.goal,
        nodes=nodes,
        mermaid=le._mermaid(nodes),  # noqa: SLF001 - helper del propio paquete
        narrative=str(data.get("narrative", "")).strip(),
    )


def _render_plan(
    session: le.LearningSession,
    bundle: MaterialBundle,
    factory: le.QuestionFactory,
) -> None:
    st.subheader("Paso 2 · Plan")
    if session.plan is None:
        with st.spinner("Construyendo el mapa de dependencias…"):
            plan = _ai_plan(session, bundle, factory)
            origin = "IA"
            if plan is None:
                plan = le.build_plan(bundle, factory, session.goal, session.strands)
                origin = "material"
            session.plan = plan
            session.note(f"Plan generado a partir de: {origin}.")

    plan = session.plan
    if not plan.nodes:
        st.error("El material no alcanza para armar un plan. Revisa el libro de la materia.")
        return

    st.markdown(plan.narrative)
    render_mermaid(plan.mermaid, height=380)

    st.markdown("#### Nodos, en el orden en que se enseñan")
    for index, node in enumerate(plan.nodes, start=1):
        kind = {
            "unconditional": "🔷 verdad incondicional",
            "derived": "🔶 idea derivada",
            "goal": "🎯 meta",
        }.get(node.kind, node.kind)
        with st.expander(f"{index}. {node.label}  ·  {kind}"):
            st.markdown(node.statement)
            if node.quote and node.quote != node.statement:
                st.markdown(f'> {node.quote}')
            if node.source:
                st.caption(f"Fuente: {node.source}")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Aprobar plan y empezar la lección", type="primary"):
            session.plan.approved = True
            session.phase = "leccion"
            session.current_index = 0
            session.note("Plan aprobado por el estudiante.")
            st.rerun()
    with col2:
        if st.button("Rehacer con otro enfoque"):
            session.plan = None
            st.rerun()

    st.caption(
        "El plan es un punto de control: si una raíz está mal elegida, corregirla "
        "aquí es barato; a mitad de la lección, no."
    )


# ---------------------------------------------------------------------------
# Fase 3 · Lección
# ---------------------------------------------------------------------------

def _node_step(
    session: le.LearningSession,
    bundle: MaterialBundle,
    factory: le.QuestionFactory,
    node: "le.TeachNode",
) -> tuple[le.LessonStep, str | None]:
    """Devuelve el paso y, si la IA narró, el texto generado."""
    cache_key = f"ap_step:{session.session_id}:{node.id}"
    step = st.session_state.get(cache_key)
    if step is None:
        teacher = le.Teacher(bundle, session.plan, factory)
        step = teacher.step(node)
        st.session_state[cache_key] = step

    narrative_key = f"ap_ai_text:{session.session_id}:{node.id}"
    narrative = st.session_state.get(narrative_key)
    client = _ai_client()
    if narrative is None and session.ai_mode == "ia" and client.available:
        previous = [
            other.label for other in session.plan.nodes[: session.current_index]
        ]
        try:
            with st.spinner("Redactando la explicación…"):
                narrative = client.chat(build_teacher_messages(
                    session.materia,
                    session.goal,
                    node.label,
                    node.statement,
                    node.quote,
                    node.source,
                    previous,
                ))
        except AIError as exc:
            st.warning(f"La IA no respondió ({exc}). Se muestra el texto del material.")
            narrative = ""
        st.session_state[narrative_key] = narrative
    return step, (narrative or None)


def _render_lesson(
    session: le.LearningSession,
    bundle: MaterialBundle,
    factory: le.QuestionFactory,
) -> None:
    plan = session.plan
    nodes = plan.nodes
    if session.current_index >= len(nodes):
        session.phase = "cierre"
        st.rerun()
        return

    st.subheader("Paso 3 · Lección")
    st.progress(
        session.current_index / max(len(nodes), 1),
        text=f"Nodo {session.current_index + 1} de {len(nodes)}",
    )

    node = nodes[session.current_index]
    step, narrative = _node_step(session, bundle, factory, node)
    progress = session.progress_for(node.id)

    kind_label = {
        "unconditional": "🔷 Verdad incondicional",
        "derived": "🔶 Idea derivada",
        "goal": "🎯 Meta",
    }.get(node.kind, node.kind)
    st.markdown(f"### {node.label}")
    st.caption(kind_label + (f" · Fuente: {node.source}" if node.source else ""))

    with st.container(border=True):
        st.markdown("**1 · Por qué ahora**")
        st.markdown(step.motivate)

        st.markdown("**2 · La idea**")
        if narrative:
            st.markdown(narrative)
            with st.expander("Texto literal del material"):
                st.markdown(step.establish)
                if node.quote:
                    st.markdown(f'> {node.quote}')
        else:
            st.markdown(step.establish)
            if node.quote and node.quote != node.statement:
                st.markdown(f'> {node.quote}')

        st.markdown("**3 · Cómo se conecta**")
        st.markdown(step.connect)

    st.markdown("**4 · Comprobación**")
    question = step.question
    if question is None:
        st.info("No hay una pregunta posible para este nodo con el material actual.")
        if st.button("Continuar →", type="primary"):
            progress.status = "superado"
            session.current_index += 1
            st.rerun()
        return

    result = ask_question(question, f"lesson:{session.session_id}:{node.id}")
    if result is None:
        return

    attempt_key = f"lesson:attempted:{session.session_id}:{question.key}"
    if not st.session_state.get(attempt_key):
        progress.attempts += 1
        st.session_state[attempt_key] = True

    if result["ok"]:
        if st.button("Continuar →", type="primary", key=f"next:{node.id}"):
            progress.status = "superado"
            session.note(f"Nodo «{node.label}» superado a la primera." if progress.attempts == 1
                         else f"Nodo «{node.label}» superado tras {progress.attempts} intentos.")
            session.current_index += 1
            st.rerun()
    else:
        st.markdown(
            "Este nodo todavía no está fijo. Léelo otra vez y vuelve a intentarlo; "
            "si sigues, lo marco para repasar."
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Reintentar", key=f"retry:{node.id}"):
                clear_question(question, f"lesson:{session.session_id}:{node.id}")
                st.rerun()
        with col2:
            if st.button("Seguir y marcarlo para repasar", key=f"skip:{node.id}"):
                progress.status = "flojo"
                progress.notes = f"Falló en «{question.correct_text[:80]}»"
                session.note(f"Nodo «{node.label}» marcado para repasar.")
                session.current_index += 1
                st.rerun()


# ---------------------------------------------------------------------------
# Cierre
# ---------------------------------------------------------------------------

def _render_closing(session: le.LearningSession) -> None:
    st.subheader("Cierre")
    st.success("Lección terminada.")
    st.markdown(f"**Meta:** {session.goal}")
    total = session.total_nodes()
    st.metric("Nodos completados", f"{session.completed_nodes}/{total}")

    st.markdown("#### Sondeo")
    st.markdown(session.probe_summary())

    weak = session.weak_concepts()
    if weak:
        st.warning("Para repasar: " + ", ".join(f"«{concept}»" for concept in weak))
    else:
        st.info("Sin puntos débiles detectados en esta sesión.")

    with st.expander("Mapa de dependencias"):
        render_mermaid(session.plan.mermaid if session.plan else "", height=340)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Guardar sesión", type="primary"):
            path = session.save(APRENDIZAJE_DIR)
            st.session_state["ap_saved"] = str(path)
            st.success(f"Guardada en {path.name}")
    with col2:
        if st.button("Nueva sesión"):
            for key in [k for k in st.session_state if k.startswith("ap_")]:
                st.session_state.pop(key, None)
            for key in [k for k in st.session_state if k.startswith("lesson:")]:
                st.session_state.pop(key, None)
            for key in [k for k in st.session_state if k.startswith("probe:")]:
                st.session_state.pop(key, None)
            st.rerun()

    saved = st.session_state.get("ap_saved")
    if saved and pathlib.Path(saved).exists():
        st.download_button(
            "⬇️ Descargar la sesión (.md)",
            data=pathlib.Path(saved).read_text(encoding="utf-8"),
            file_name=pathlib.Path(saved).name,
            mime="text/markdown",
        )


# ---------------------------------------------------------------------------
# Ruta guiada
# ---------------------------------------------------------------------------

def _render_route() -> None:
    session: le.LearningSession | None = st.session_state.get("ap_session")
    if session is None:
        _render_setup()
        return

    _ai_badge(session)
    bundle = st.session_state.get("ap_bundle")
    factory = st.session_state.get("ap_factory")
    if bundle is None or factory is None:
        bundle, factory = _get_context(session.materia)
        st.session_state["ap_bundle"] = bundle
        st.session_state["ap_factory"] = factory

    header = st.columns([3, 1])
    with header[0]:
        st.markdown(f"**{session.materia}** · meta: {session.goal}")
    with header[1]:
        st.caption(f"Sesión {session.session_id}")

    phase = session.phase
    if phase == "sondeo":
        _render_probe(session, factory)
    elif phase == "plan":
        _render_plan(session, bundle, factory)
    elif phase == "leccion":
        _render_lesson(session, bundle, factory)
    elif phase == "cierre":
        _render_closing(session)
    else:
        session.phase = "sondeo"
        st.rerun()

    with st.expander("Material que se está usando"):
        rows = format_sources(bundle)
        if rows:
            st.dataframe(rows, hide_index=True, width="stretch")
        level, message = bundle.quality()
        st.caption(f"Calidad del material: **{level}** — {message}")
        if bundle.notes:
            for note in bundle.notes:
                st.caption(f"⚠️ {note}")


# ---------------------------------------------------------------------------
# Quiz libre
# ---------------------------------------------------------------------------

def _render_free_quiz() -> None:
    st.subheader("Quiz sobre el material")
    st.markdown(
        "Las preguntas se construyen con las definiciones y frases del libro: "
        "la respuesta correcta y los distractores son afirmaciones reales del texto."
    )
    materias = _materias_con_texto_primero()
    if not materias:
        st.info("Crea una materia primero.")
        return

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        materia = st.selectbox("Materia", materias, key="q_materia")
    with col2:
        cantidad = st.slider("Preguntas", 3, 10, 5, key="q_cantidad")
    with col3:
        st.write("")
        st.write("")
        generar = st.button("Generar quiz", type="primary", key="q_generar")

    bundle, factory = _get_context(materia)
    if not bundle.has_content:
        st.caption("Esta materia aún no tiene texto aprovechable. Importa el libro primero.")
        return

    if generar:
        concepts = [d.term for d in factory.definitions]
        if not concepts:
            st.warning("No se encontraron definiciones suficientes en el material.")
            return
        # Prioriza conceptos con más presencia en el texto.
        concepts.sort(key=lambda c: -len(factory.sentences_with(c)))
        questions = factory.quiz(concepts, size=cantidad)
        if not questions:
            st.warning("No se pudieron construir preguntas con este material.")
            return
        st.session_state["q_quiz"] = questions
        st.session_state["q_index"] = 0
        st.session_state["q_hits"] = 0
        st.session_state["q_done"] = False
        for key in [k for k in st.session_state if k.startswith("quizq:")]:
            st.session_state.pop(key, None)

    questions = st.session_state.get("q_quiz")
    if not questions:
        return

    if st.session_state.get("q_done"):
        total = len(questions)
        hits = st.session_state.get("q_hits", 0)
        st.metric("Resultado", f"{hits}/{total}", help="Aciertos a la primera")
        if hits == total:
            st.success("Todas correctas.")
        elif hits >= total * 0.6:
            st.info("Bien. Revisa las que fallaste.")
        else:
            st.warning("Conviene repasar el material antes de seguir.")
        if st.button("Otro quiz"):
            st.session_state.pop("q_quiz", None)
            st.session_state["q_done"] = False
            st.rerun()
        return

    index = st.session_state.get("q_index", 0)
    question = questions[index]
    st.progress((index + 1) / len(questions), text=f"Pregunta {index + 1} de {len(questions)}")
    st.markdown(f"#### {question.prompt}")
    result = ask_question(question, "quizq")

    if result is None:
        return
    if st.button("Siguiente →", type="primary", key=f"q_next:{index}"):
        if result["ok"]:
            st.session_state["q_hits"] = st.session_state.get("q_hits", 0) + 1
        if index + 1 >= len(questions):
            st.session_state["q_done"] = True
        else:
            st.session_state["q_index"] = index + 1
        st.rerun()


# ---------------------------------------------------------------------------
# Diagramas
# ---------------------------------------------------------------------------

def render_mermaid(code: str, height: int = 420) -> None:
    """Renderiza un diagrama Mermaid en un iframe aislado."""
    if not code.strip():
        return
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
<style>
  body {{ margin:0; background:transparent; font-family: system-ui, sans-serif; }}
  .mermaid {{ display:flex; justify-content:center; }}
</style>
</head>
<body>
<div class="mermaid">{code}</div>
<script>
  if (window.mermaid) {{
    mermaid.initialize({{ startOnLoad: true, theme: 'neutral', securityLevel: 'loose' }});
  }} else {{
    document.body.innerHTML =
      '<p style="color:#b00;font-size:13px">No se pudo cargar Mermaid ' +
      '(se necesita conexión a internet). El código está abajo.</p>';
  }}
</script>
</body>
</html>"""
    try:
        st.iframe(html, height=height)
    except Exception:
        st.code(code, language="mermaid")


MERMAID_TEMPLATES = {
    "Modelo ABC (Ellis)": """graph TD
    A[Evento activador] --> B[Creencias]
    B --> C[Consecuencias emocionales]
    B -.-> D[Disputa]
    D --> E[Nuevo efecto]
    style B fill:#fff3e0
    style D fill:#e8f5e9""",
    "Ciclo de la ansiedad": """graph LR
    A[Situación] --> B[Pensamiento automático]
    B --> C[Ansiedad]
    C --> D[Evitación]
    D --> A
    style C fill:#ffebee""",
    "Jerarquía de necesidades": """graph TD
    A[Fisiológicas] --> B[Seguridad]
    B --> C[Pertenencia]
    C --> D[Estima]
    D --> E[Autorrealización]
    style E fill:#e8f5e9""",
    "Flujo de la TCC": """graph TD
    A[Evaluación] --> B[Psicoeducación]
    B --> C[Identificar pensamientos]
    C --> D[Cuestionar evidencia]
    D --> E[Reestructuración]
    E --> F[Experimentos conductuales]
    F --> G[Prevención de recaídas]""",
}


def _render_diagrams() -> None:
    st.subheader("Diagramas")
    st.markdown(
        "Un diagrama sirve cuando la idea es una estructura: dependencias, flujos o "
        "jerarquías. Si no aclara más que una frase, no hace falta."
    )
    session = st.session_state.get("ap_session")
    if session and session.plan:
        st.markdown("#### Mapa de la sesión actual")
        render_mermaid(session.plan.mermaid, height=380)
        st.divider()

    plantilla = st.selectbox("Plantilla", list(MERMAID_TEMPLATES), key="diag_template")
    codigo = st.text_area(
        "Código Mermaid (editable)",
        value=MERMAID_TEMPLATES[plantilla],
        height=200,
        key=f"diag_code_{list(MERMAID_TEMPLATES).index(plantilla)}",
    )
    render_mermaid(codigo, height=360)
    with st.expander("Ver el código"):
        st.code(codigo, language="mermaid")


# ---------------------------------------------------------------------------
# Bitácora
# ---------------------------------------------------------------------------

def _render_log() -> None:
    st.subheader("Bitácora de sesiones")
    entries = le.list_sessions(APRENDIZAJE_DIR)
    if not entries:
        st.info("Todavía no hay sesiones guardadas.")
        return

    materias = sorted({entry["materia"] for entry in entries if entry["materia"]})
    filtro = st.selectbox("Filtrar por materia", ["Todas"] + materias, key="log_filtro")
    if filtro != "Todas":
        entries = [entry for entry in entries if entry["materia"] == filtro]

    for entry in entries:
        titulo = f"{entry['meta'] or 'Sesión'} · {entry['materia']} · {entry['fecha'][:10]}"
        with st.expander(titulo):
            st.caption(entry["preview"])
            col1, col2, col3 = st.columns(3)
            with col1:
                st.download_button(
                    "⬇️ Descargar",
                    data=entry["content"],
                    file_name=entry["name"],
                    mime="text/markdown",
                    key=f"dl:{entry['name']}",
                )
            with col2:
                confirm = st.checkbox("Confirmar", key=f"cf:{entry['name']}")
                if st.button("🗑️ Eliminar", key=f"rm:{entry['name']}", disabled=not confirm):
                    try:
                        pathlib.Path(entry["path"]).unlink()
                    except OSError as exc:
                        st.error(f"No se pudo eliminar: {exc}")
                    else:
                        st.rerun()
            with col3:
                st.caption(entry["motor"] or "—")


# ---------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------

def render_aprender_section() -> None:
    st.header("🎓 Aprender")
    st.markdown(
        "Un sistema para estudiar de verdad: primero se localiza tu borde, luego se "
        "dibuja el mapa y sólo entonces se enseña, nodo por nodo. "
        "Basado en [amosblomqvist/learn](https://github.com/amosblomqvist/learn)."
    )

    with st.expander("Cómo funciona (y un ejemplo guiado)"):
        st.markdown(le.PHILOSOPHY)
        st.divider()
        st.markdown(DEMO_EXAMPLE)

    tab_ruta, tab_quiz, tab_diag, tab_log = st.tabs(
        ["🧭 Ruta guiada", "❓ Quiz", "📊 Diagramas", "📁 Bitácora"]
    )
    with tab_ruta:
        _render_route()
    with tab_quiz:
        _render_free_quiz()
    with tab_diag:
        _render_diagrams()
    with tab_log:
        _render_log()


def run_aprender() -> None:
    """Punto de entrada desde el menú principal."""
    render_aprender_section()


if __name__ == "__main__":
    run_aprender()
