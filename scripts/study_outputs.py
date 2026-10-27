#!/usr/bin/env python3
"""
Salidas de estudio reales a partir del material de una materia.

Las pantallas «Analizar EPUB», «Asistente de escritura» y «PowerPoint con
imágenes» comparten este módulo. Sin IA, todo se construye con el texto del
libro (secciones, definiciones, frases y referencias). Con IA configurada, se
pide redacción al modelo y se cae con elegancia al modo local si falla.

Nada aquí inventa contenido: si el material no da para algo, se dice.
"""

from __future__ import annotations

import pathlib
import re
from typing import Sequence

from material import MaterialBundle, Paragraph, _fold
import learn_engine as le
from llm_provider import AIClient, AIConfig, AIError


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _cite(bundle: MaterialBundle) -> str:
    """Referencia APA del material usado (libro o archivo convertido)."""
    for path, kind, chars in bundle.sources:
        name = pathlib.Path(path).stem
        if chars > 2000:
            title = name.replace("_", " ").strip()
            return f"{title}. (s. f.). *Material de estudio de {bundle.materia}* [Documento]. "
    return f"Material de estudio de {bundle.materia}. (s. f.)."


def _excerpt(source: object, limit: int = 320) -> str:
    """Recorta un párrafo o una cadena a una longitud legible."""
    text = getattr(source, "text", None)
    if text is None:
        text = str(source)
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


def _topic_paragraphs(bundle: MaterialBundle, topic: str, limit: int = 8) -> list[Paragraph]:
    return bundle.related(topic, limit=limit)


def _client() -> AIClient:
    return AIClient(AIConfig.load())


def ai_status() -> tuple[bool, str]:
    config = AIConfig.load()
    client = AIClient(config)
    if not client.available:
        return False, "Sin IA configurada: se genera desde el material."
    return True, config.describe()


def _try_ai(system: str, user: str, *, max_tokens: int = 1400) -> tuple[str | None, str]:
    """Devuelve (texto | None, motivo)."""
    client = _client()
    if not client.available:
        return None, "IA no configurada"
    try:
        text = client.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=max_tokens,
        )
    except AIError as exc:
        return None, str(exc)
    if not text.strip():
        return None, "respuesta vacía"
    return text.strip(), "ok"


# ---------------------------------------------------------------------------
# Guía de estudio
# ---------------------------------------------------------------------------

def study_guide(bundle: MaterialBundle, topic: str, *, use_ai: bool = True) -> tuple[str, str]:
    """Devuelve (markdown, motor) con una guía de estudio verificable."""
    if use_ai:
        excerpts = "\n\n".join(
            f"[{pathlib.Path(p.source).name} · {' > '.join(p.heading_path)}]\n{_excerpt(p, 600)}"
            for p in _topic_paragraphs(bundle, topic, 6)
        )
        system = (
            "Eres profesor de psicología clínica. Escribes guías de estudio en "
            "español, en Markdown, apoyándote sólo en los extractos que recibes. "
            "Si algo no está en los extractos, no lo afirmes."
        )
        user = (
            f"Materia: {bundle.materia}\nTema: {topic}\n\n"
            f"Extractos del material:\n{excerpts}\n\n"
            "Escribe una guía con: 1) ideas centrales, 2) conceptos y definiciones, "
            "3) relaciones entre conceptos, 4) seis preguntas de repaso con respuesta "
            "breve, 5) qué conviene leer del material para cerrar huecos."
        )
        text, reason = _try_ai(system, user)
        if text:
            return text, "ia"

    return _local_study_guide(bundle, topic), "local"


def _local_study_guide(bundle: MaterialBundle, topic: str) -> str:
    paragraphs = _topic_paragraphs(bundle, topic, 6)
    relevant_definitions = [
        definition for definition in bundle.definitions
        if _fold(definition.term) in _fold(topic)
        or any(_fold(definition.term) in _fold(p.text) for p in paragraphs)
    ][:8]
    truths = [
        truth for truth in bundle.truths
        if any(_fold(truth.text) in _fold(p.text) for p in paragraphs)
        or _fold(topic) in _fold(truth.text)
    ][:4]
    sections = [
        section for section in bundle.sections
        if section.level <= 3 and section.chars > 0
    ][:8]

    lines = [
        f"# Guía de estudio: {topic}",
        "",
        f"*Materia: {bundle.materia} · generada con el texto del material "
        f"({bundle.total_chars:,} caracteres revisados).*".replace(",", "."),
        "",
        "## 1. De qué trata (según el material)",
        "",
    ]
    if paragraphs:
        for paragraph in paragraphs[:4]:
            source = pathlib.Path(paragraph.source).name
            lines.append(f"- {_excerpt(paragraph, 260)}  \n  *({source})*")
    else:
        lines.append("- No se encontró texto relacionado con este tema en el material.")

    lines += ["", "## 2. Conceptos y definiciones del texto", ""]
    if relevant_definitions:
        for definition in relevant_definitions:
            lines.append(f"- **{definition.term}** — {definition.body}")
    else:
        lines.append("- No se detectaron definiciones explícitas para este tema.")

    lines += ["", "## 3. Afirmaciones que el material sostiene sin excepciones", ""]
    if truths:
        for truth in truths:
            lines.append(f"- {truth.text}")
    else:
        lines.append("- No se detectaron afirmaciones universales sobre este tema.")

    lines += ["", "## 4. Preguntas de repaso", ""]
    factory = le.QuestionFactory(bundle)
    concepts = [definition.term for definition in relevant_definitions]
    questions = factory.quiz(concepts, size=6) if concepts else []
    if questions:
        for index, question in enumerate(questions, 1):
            prompt = re.sub(r"\s+", " ", question.prompt)
            explanation = re.sub(r"\s+", " ", question.explanation)
            lines.append(f"{index}. {prompt}")
            lines.append(f"   - **Respuesta:** {question.correct_text}")
            lines.append(f"   - {explanation}")
            lines.append("")
    else:
        lines.append("No hay suficientes definiciones para generar preguntas de este tema.")

    lines += ["", "## 5. Dónde seguir leyendo", ""]
    if sections:
        for section in sections:
            lines.append(f"- «{section.title}» (nivel {section.level})")
    else:
        lines.append("- Revisa los capítulos del libro importado.")

    lines += [
        "",
        "---",
        "",
        "## Referencias",
        "",
        _cite(bundle),
        "",
        "*Guía generada a partir del material importado. Revisa las citas antes de "
        "entregar un trabajo académico.*",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Estructura de trabajo académico (APA 7)
# ---------------------------------------------------------------------------

_APA_SECTIONS = {
    "Ensayo": ["Introducción", "Desarrollo", "Conclusión"],
    "Trabajo de investigación": ["Introducción", "Método", "Resultados", "Discusión"],
    "Reflexión": ["Introducción", "Desarrollo reflexivo", "Conclusión"],
    "Análisis de caso": ["Introducción", "Descripción del caso", "Análisis", "Conclusión"],
    "Revisión teórica": ["Introducción", "Desarrollo teórico", "Discusión", "Conclusión"],
}


def writing_outline(
    bundle: MaterialBundle,
    topic: str,
    tipo_trabajo: str,
    *,
    autor: str = "",
    institucion: str = "",
    profesor: str = "",
    use_ai: bool = True,
) -> tuple[str, str]:
    sections = _APA_SECTIONS.get(tipo_trabajo, ["Introducción", "Desarrollo", "Conclusión"])
    if use_ai:
        excerpts = "\n\n".join(
            f"[{pathlib.Path(p.source).name}] {_excerpt(p, 500)}"
            for p in _topic_paragraphs(bundle, topic, 5)
        )
        system = (
            "Eres un asesor académico experto en APA 7. Propones estructuras de "
            "trabajo, no el trabajo completo. Te apoyas sólo en los extractos dados "
            "y marcas con [COMPLETAR] lo que el estudiante debe desarrollar."
        )
        user = (
            f"Materia: {bundle.materia}\nTema: {topic}\nTipo: {tipo_trabajo}\n"
            f"Secciones requeridas: {', '.join(sections)}\n\n"
            f"Extractos del material:\n{excerpts}\n\n"
            "Devuelve Markdown con: portada APA, resumen con palabras clave, cada "
            "sección con 3-5 puntos concretos citando el material, y referencias."
        )
        text, reason = _try_ai(system, user, max_tokens=1600)
        if text:
            return text, "ia"

    return _local_outline(
        bundle, topic, tipo_trabajo, sections, autor, institucion, profesor
    ), "local"


def _local_outline(
    bundle: MaterialBundle,
    topic: str,
    tipo_trabajo: str,
    sections: Sequence[str],
    autor: str,
    institucion: str,
    profesor: str,
) -> str:
    paragraphs = _topic_paragraphs(bundle, topic, 5)
    definitions = [
        d for d in bundle.definitions if _fold(d.term) in _fold(topic)
    ][:4]

    lines = [
        f"# {topic.title()}",
        "",
        autor or "[Nombre del estudiante]",
        "",
        institucion or "[Universidad]",
        "",
        f"{bundle.materia}",
        "",
        profesor or "[Nombre del docente]",
        "",
        "[Mes Año]",
        "",
        "---",
        "",
        "## Resumen",
        "",
        f"[Escribe 150-250 palabras sobre {topic}. Parte de esta idea del material: "
        f"«{_excerpt(paragraphs[0], 180) if paragraphs else 'sin extracto disponible'}»]",
        "",
        f"**Palabras clave:** {', '.join([topic.lower()] + [d.term.lower() for d in definitions[:3]])}",
        "",
        "---",
        "",
    ]

    for index, section in enumerate(sections, start=1):
        lines += [f"## {section}", ""]
        if index == 1 and definitions:
            lines.append(
                "Define el problema con el vocabulario del material:"
            )
            for definition in definitions:
                lines.append(f"- **{definition.term}**: {definition.body}")
            lines.append("")
        if paragraphs:
            lines.append("Puntos que el material ya sostiene (úsalos como base):")
            for paragraph in paragraphs[:3]:
                lines.append(f"- {_excerpt(paragraph, 220)}")
            lines.append("")
        lines += [
            f"[COMPLETAR: desarrolla «{section}» en 2-3 párrafos con sangría APA y "
            "citas en formato (Autor, Año).]",
            "",
            "---",
            "",
        ]

    lines += [
        "## Referencias",
        "",
        _cite(bundle),
        "",
        "[Añade aquí las fuentes que cites en el texto, en orden alfabético y con "
        "sangría francesa de 1,27 cm.]",
        "",
        "---",
        "",
        "*Estructura generada a partir del material importado. El contenido entre "
        "corchetes lo escribes tú: la herramienta no redacta tu trabajo.*",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Estructura de PowerPoint
# ---------------------------------------------------------------------------

def slides_outline(
    bundle: MaterialBundle,
    topic: str,
    *,
    materia: str,
    n_slides: int = 12,
    use_ai: bool = True,
) -> tuple[str, str]:
    if use_ai:
        excerpts = "\n\n".join(
            f"[{pathlib.Path(p.source).name}] {_excerpt(p, 500)}"
            for p in _topic_paragraphs(bundle, topic, 5)
        )
        system = (
            "Eres diseñador de presentaciones académicas. Propones diapositivas "
            "claras, una idea por diapositiva, con notas del ponente. Sólo usas el "
            "material entregado; si falta una imagen, lo dices."
        )
        user = (
            f"Materia: {materia}\nTema: {topic}\nDiapositivas: {n_slides}\n\n"
            f"Extractos:\n{excerpts}\n\n"
            "Devuelve Markdown con una sección por diapositiva: título, 3-5 viñetas, "
            "una cita del material y notas del ponente."
        )
        text, reason = _try_ai(system, user, max_tokens=1800)
        if text:
            return text, "ia"

    return _local_slides(bundle, topic, materia, n_slides), "local"


def _local_slides(
    bundle: MaterialBundle, topic: str, materia: str, n_slides: int
) -> str:
    paragraphs = _topic_paragraphs(bundle, topic, max(4, n_slides - 2))
    definitions = [
        d for d in bundle.definitions if _fold(d.term) in _fold(topic)
    ][:4]
    sections = [s.title for s in bundle.sections if s.level in (2, 3)][:8]

    lines = [
        f"# Estructura de PowerPoint: {topic}",
        "",
        f"**Materia:** {materia}",
        f"**Diapositivas previstas:** {max(n_slides, len(paragraphs) + 3)}",
        "",
        "---",
        "",
        "### Diapositiva 1 — Portada",
        f"**Título:** {topic}",
        f"**Subtítulo:** {materia}",
        "**Notas del ponente:** Presenta el tema y di por qué importa en una frase.",
        "",
        "### Diapositiva 2 — Agenda",
        "",
    ]
    for section in sections[:5]:
        lines.append(f"- {section}")
    lines += ["", "**Notas del ponente:** Recorre la agenda en 30 segundos.", "", "---", ""]

    for index, paragraph in enumerate(paragraphs, start=3):
        heading = paragraph.heading_path[-1] if paragraph.heading_path else topic
        lines += [
            f"### Diapositiva {index} — {heading}",
            "**Contenido:**",
            f"- {_excerpt(paragraph, 150)}",
        ]
        if index - 3 < len(definitions):
            definition = definitions[index - 3]
            lines.append(f"- **{definition.term}**: {_excerpt(definition.body, 120)}")
        lines += [
            f"**Cita del material:** «{_excerpt(paragraph, 110)}»",
            "**Notas del ponente:** Explica la idea con un ejemplo propio y conecta "
            "con la diapositiva anterior.",
            "",
            "---",
            "",
        ]

    lines += [
        f"### Diapositiva {len(paragraphs) + 3} — Conclusiones",
        "**Contenido:**",
        "- Retoma las tres ideas centrales del material.",
        "- Señala qué queda abierto.",
        "",
        "**Notas del ponente:** Cierra con una frase que el público pueda repetir.",
        "",
        "---",
        "",
        "## Referencias",
        "",
        _cite(bundle),
        "",
        "*Las imágenes deben salir del propio material (figuras del libro). Si no hay "
        "figura para una diapositiva, no se inventa: se omite.*",
    ]
    return "\n".join(lines)
