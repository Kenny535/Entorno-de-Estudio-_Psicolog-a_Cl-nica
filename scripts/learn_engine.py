#!/usr/bin/env python3
"""
Motor de aprendizaje basado en amosblomqvist/learn.

Implementa los dos principios del repositorio original y su proceso completo:

    Principio i  — Verdades incondicionales primero.
    Principio ii — «¿Cómo podría haberlo descubierto yo?»: cada paso se motiva.
    Proceso      — Sondear (nivel y meta) → Planear (DAG) → Enseñar (nodo a nodo).

No importa Streamlit: es lógica pura y se puede probar sin interfaz.

Las preguntas se construyen **desde el texto del material**, no desde
plantillas. La respuesta correcta y los distractores salen del mismo libro, de
modo que cada opción es una afirmación real del material sobre otro concepto.
"""

from __future__ import annotations

import random
import re
import zlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Sequence

from material import Definition, MaterialBundle, Paragraph, _fold, split_sentences

# ---------------------------------------------------------------------------
# Filosofía (se muestra en la interfaz y se usa como contexto del modelo)
# ---------------------------------------------------------------------------

PHILOSOPHY = """\
## Principio i — Verdades incondicionales primero
Empieza por el suelo. Fija los hechos **siempre verdaderos** que se aceptan tal
cual, sin matices ni condiciones, antes de construir nada encima. No porque sea
el orden lógico «correcto», sino porque son lo más fácil de aceptar y fijar: son
seguros, así que se graban de inmediato y dan la primera base firme.

## Principio ii — «¿Cómo podría haberlo descubierto yo?»
Un hecho sin motivo visible se siente arbitrario y el cerebro no lo fija. Cada
paso debe sentirse descubierto, no decretado: por qué necesitamos esto, por qué
este paso y no otro. Se construyen así los **enlaces** entre ideas, no sólo los
nodos.

## La meta: el clic
El momento en que un montón de hechos sueltos colapsa en unas pocas ideas
generadoras: la misma información con muchas menos piezas móviles. Ese
entendimiento se sostiene solo, porque está sujeto por sus conexiones.

## El proceso
1. **Sondear** — localizar el borde de lo que ya sabes (con aciertos y fallos)
   y aclarar qué quieres aprender.
2. **Planear** — el mapa de dependencias: raíces y meta, en orden.
3. **Enseñar** — para cada nodo: motivar → establecer → conectar → comprobar.
"""

DIFFICULTY_LABELS = {
    1: "Recordar el término",
    2: "Reconocer la descripción",
    3: "Distinguir la definición",
    4: "Ubicar en el material",
    5: "Delimitar sin excepciones",
}

_HEDGE_SENTENCE = re.compile(
    r"\b(algunos|algunas|a veces|puede|pueden|podría|podrían|suele|suelen|"
    r"tiende|tienden|generalmente|a menudo|en ocasiones|probablemente|"
    r"parece|parecen|quizá|tal vez|frecuentemente|la mayoría|no todas|no todos)\b",
    re.I,
)
_DEFINITIONAL_CUE = re.compile(
    r"\b(es|son|se refiere|consiste|consisten|implica|implican|significa|"
    r"produce|provoca|se define|se caracteriza|abarca|designa)\b",
    re.I,
)


@dataclass(frozen=True)
class Question:
    """Una pregunta calificable con su explicación y su fuente."""

    key: str
    prompt: str
    options: tuple[str, ...]
    correct: int
    explanation: str
    difficulty: int
    kind: str
    concept: str
    source: str

    @property
    def correct_text(self) -> str:
        return self.options[self.correct]

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "prompt": self.prompt,
            "options": list(self.options),
            "correct": self.correct,
            "explanation": self.explanation,
            "difficulty": self.difficulty,
            "kind": self.kind,
            "concept": self.concept,
            "source": self.source,
        }


def _stable_seed(*parts: str) -> int:
    return zlib.crc32("\u241f".join(parts).encode("utf-8"))


def _plain(text: str) -> str:
    """Quita marcas de énfasis y recompone palabras cortadas."""
    text = text.replace("*", "").replace("`", "")
    text = re.sub(r"(\w)-\s+(\w)", r"\1\2", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _trim(text: str, limit: int = 130) -> str:
    text = _plain(text)
    if len(text) <= limit:
        return text
    cut = text[:limit]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(" ,;:.") + "…"


def _clean_sentence(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^[a-záéíóúñ]\)\s*", "", text)
    return text


def _fold_contains(haystack: str, needle: str) -> bool:
    return _fold(needle) in _fold(haystack)


def _source_label(source: str, heading_path: Sequence[str]) -> str:
    name = Path(source).name
    if heading_path:
        return f"{name} · {heading_path[-1]}"
    return name


class QuestionFactory:
    """Construye preguntas cuyo contenido sale del material de la materia."""

    def __init__(self, bundle: MaterialBundle) -> None:
        self.bundle = bundle
        self.definitions: list[Definition] = [
            definition
            for definition in bundle.definitions
            if 1 <= len(definition.term.split()) <= 5
            and 25 <= len(definition.body) <= 260
        ]
        self._by_term = {_fold(d.term): d for d in self.definitions}
        self.term_pool: list[str] = [d.term for d in self.definitions]
        self.categorical: list[Definition] = [d for d in self.definitions if d.is_categorical]
        self._sentences_cache: dict[str, list[tuple[str, Paragraph]]] = {}
        self._cache: dict[tuple[str, int], Question | None] = {}
        self._section_titles = list(
            dict.fromkeys(s.title for s in bundle.sections if s.level >= 2 and len(s.title) < 60)
        )

    # -- consultas --------------------------------------------------------
    def sentences_with(self, concept: str) -> list[tuple[str, Paragraph]]:
        key = _fold(concept)
        if key in self._sentences_cache:
            return self._sentences_cache[key]
        pattern = re.compile(r"\b" + re.escape(concept) + r"\b", re.I)
        found: list[tuple[str, Paragraph]] = []
        if len(concept) < 4:
            self._sentences_cache[key] = found
            return found
        for paragraph in self.bundle.paragraphs:
            if concept.lower() not in paragraph.text.lower():
                continue
            for sentence in split_sentences(paragraph.text):
                if pattern.search(sentence) and 70 <= len(sentence) <= 260:
                    found.append((_clean_sentence(sentence), paragraph))
        self._sentences_cache[key] = found
        return found

    def has_material(self, concept: str) -> bool:
        return _fold(concept) in self._by_term or len(self.sentences_with(concept)) >= 1

    def _sections_of(self, concept: str) -> list[str]:
        definition = self._by_term.get(_fold(concept))
        if definition is not None:
            return list(definition.heading_path)
        found = self.sentences_with(concept)
        return list(found[0][1].heading_path) if found else []

    def _distractor_terms(
        self, concept: str, count: int, *, forbid_in: str = ""
    ) -> list[str]:
        target = _fold(concept)
        words = len(concept.split())
        sections = {_fold(section) for section in self._sections_of(concept)}
        forbidden_text = _fold(forbid_in)
        scored: list[tuple[int, int, str]] = []
        seen: set[str] = set()
        for other in self.term_pool:
            key = _fold(other)
            if key == target or key in seen or len(other) < 3:
                continue
            if forbid_in and key in forbidden_text:
                continue
            seen.add(key)
            score = 0
            if abs(len(other.split()) - words) == 0:
                score += 2
            if abs(len(other) - len(concept)) <= 8:
                score += 2
            if sections and sections & {_fold(section) for section in self._sections_of(other)}:
                score += 3
            if key[:4] == target[:4]:
                score += 1
            scored.append((-score, _stable_seed(concept, other), other))
        scored.sort()
        return [term for _, _, term in scored[:count]]

    # -- tipos de pregunta ------------------------------------------------
    def cloze(self, concept: str) -> Question | None:
        candidates = self.sentences_with(concept)
        if not candidates:
            return None
        pattern = re.compile(r"\b" + re.escape(concept) + r"\b", re.I)
        scored: list[tuple[int, int, str, Paragraph]] = []
        for sentence, paragraph in candidates:
            occurrences = pattern.findall(sentence)
            # Si el término aparece dos veces, al tapar una queda la otra a la
            # vista y la pregunta se responde sola.
            if len(occurrences) != 1:
                continue
            position = _fold(sentence).find(_fold(concept)) / max(len(sentence), 1)
            score = 0
            if 90 <= len(sentence) <= 210:
                score += 2
            if position < 0.45:
                score += 2
            if position > 0.05:
                score += 1
            if _DEFINITIONAL_CUE.search(sentence):
                score += 2
            if len(concept.split()) > 1:
                score += 1
            scored.append((-score, _stable_seed(sentence), sentence, paragraph))
        if not scored:
            return None
        scored.sort()
        _, _, sentence, paragraph = scored[0]
        blanked = pattern.sub("_____", sentence, count=1)
        if "_____" not in blanked or len(blanked) < 60:
            return None
        distractors = self._distractor_terms(concept, 3, forbid_in=blanked)
        options = [concept] + distractors
        if len(options) < 3:
            return None
        return self._finalise(
            kind="cloze",
            concept=concept,
            difficulty=1,
            prompt=f"Completa la frase del material:\n\n«{blanked}»",
            options=options,
            correct_value=concept,
            explanation=(
                f"El material dice: «{sentence}»\n\n"
                f"Fuente: {_source_label(paragraph.source, paragraph.heading_path)}"
            ),
            source=paragraph.source,
            heading_path=paragraph.heading_path,
        )

    def reverse(self, concept: str) -> Question | None:
        """Dada la descripción, elegir el término (reconocimiento)."""
        definition = self._by_term.get(_fold(concept))
        if definition is None or not definition.is_categorical:
            return None
        distractors = self._distractor_terms(concept, 3, forbid_in=definition.body)
        options = [definition.term] + distractors
        if len(options) < 3:
            return None
        return self._finalise(
            kind="reconocer",
            concept=concept,
            difficulty=2,
            prompt=(
                "¿Qué término del material corresponde a esta descripción?\n\n"
                f"«{_trim(definition.body, 180)}»"
            ),
            options=options,
            correct_value=definition.term,
            explanation=(
                f"«{definition.term}» — {definition.body}\n\n"
                f"Fuente: {_source_label(definition.source, definition.heading_path)}"
            ),
            source=definition.source,
            heading_path=definition.heading_path,
        )

    def definition(self, concept: str, *, close: bool) -> Question | None:
        definition = self._by_term.get(_fold(concept))
        if definition is None or not definition.is_categorical:
            return None
        pool = self.categorical
        if close:
            same = [d for d in pool if d.heading_path and d.heading_path == definition.heading_path]
            if len(same) >= 4:
                pool = same
        distractors = [
            d for d in pool
            if _fold(d.term) != _fold(definition.term)
            and not _fold_contains(d.body, definition.term)
            and not _fold_contains(definition.body, d.term)
        ]
        body_length = len(definition.body)
        distractors = [
            d for d in distractors
            if 0.45 <= len(d.body) / max(body_length, 1) <= 2.2
        ]
        distractors.sort(key=lambda d: _stable_seed(concept, d.term))
        chosen = [_trim(d.body, 150) for d in distractors[:3]]
        options = [_trim(definition.body, 150)] + chosen
        if len(options) < 3:
            return None
        return self._finalise(
            kind="definir" if not close else "distinguir",
            concept=concept,
            difficulty=3,
            prompt=f"Según el material, ¿qué se afirma de «{definition.term}»?",
            options=options,
            correct_value=_trim(definition.body, 150),
            explanation=(
                f"«{definition.sentence}»\n\n"
                f"Fuente: {_source_label(definition.source, definition.heading_path)}"
            ),
            source=definition.source,
            heading_path=definition.heading_path,
        )

    def section_of(self, concept: str) -> Question | None:
        sections = self._sections_of(concept)
        if not sections:
            return None
        target = sections[-1]
        pool = [title for title in self._section_titles if title != target]
        if len(pool) < 3:
            return None
        pool.sort(key=lambda title: _stable_seed(concept, title))
        chosen: list[str] = []
        for title in pool:
            if title not in chosen:
                chosen.append(title)
            if len(chosen) == 3:
                break
        if len(chosen) < 2:
            return None
        found = self.sentences_with(concept)
        source = found[0][1].source if found else ""
        heading_path = found[0][1].heading_path if found else tuple(sections)
        return self._finalise(
            kind="ubicar",
            concept=concept,
            difficulty=4,
            prompt=f"¿En qué parte del material se desarrolla «{concept}»?",
            options=[target] + chosen,
            correct_value=target,
            explanation=(
                f"«{concept}» aparece en la sección «{target}».\n\n"
                f"Fuente: {_source_label(source, heading_path)}"
            ),
            source=source,
            heading_path=heading_path,
        )

    def truth(self, concept: str = "") -> Question | None:
        truths = [
            truth for truth in self.bundle.truths
            if 45 <= len(truth.text) <= 190 and truth.strength >= 1
        ]
        if not truths:
            return None
        truths.sort(
            key=lambda t: (
                -(
                    (3 if concept and _fold_contains(t.text, concept) else 0)
                    + t.strength
                ),
                _stable_seed(t.text),
            )
        )
        correct = truths[0]
        hedged: list[str] = []
        for paragraph in self.bundle.paragraphs:
            for sentence in split_sentences(paragraph.text):
                if not 55 <= len(sentence) <= 185:
                    continue
                if "?" in sentence or "¿" in sentence:
                    continue
                if sentence.strip().startswith("("):
                    continue
                if _HEDGE_SENTENCE.search(sentence) or re.match(
                    r"^(en el otro|en este caso|por ejemplo)", sentence.strip(), re.I
                ):
                    cleaned = _trim(_clean_sentence(sentence), 150)
                    if cleaned and cleaned not in hedged:
                        hedged.append(cleaned)
                if len(hedged) >= 5:
                    break
            if len(hedged) >= 5:
                break
        if len(hedged) < 3:
            return None
        chosen = sorted(hedged, key=lambda text: _stable_seed(correct.text, text))[:3]
        return self._finalise(
            kind="delimitar",
            concept=concept or "Verdades incondicionales",
            difficulty=5,
            prompt=(
                "¿Cuál de estas afirmaciones se sostiene **sin excepciones** "
                "según el material (una verdad incondicional)?"
            ),
            options=[_trim(correct.text, 150)] + chosen,
            correct_value=_trim(correct.text, 150),
            explanation=(
                "La correcta no admite matices: no dice «algunos», «a veces» ni "
                "«puede». Las demás están condicionadas y por eso no sirven como "
                "base segura.\n\n"
                f"«{correct.text}»\n\n"
                f"Fuente: {_source_label(correct.source, correct.heading_path)}"
            ),
            source=correct.source,
            heading_path=correct.heading_path,
        )

    # -- ensamblado -------------------------------------------------------
    def _finalise(
        self,
        *,
        kind: str,
        concept: str,
        difficulty: int,
        prompt: str,
        options: Sequence[str],
        correct_value: str,
        explanation: str,
        source: str,
        heading_path: Sequence[str],
    ) -> Question | None:
        unique: list[str] = []
        for option in options:
            option = option.strip()
            if option and option not in unique:
                unique.append(option)
        if len(unique) < 3 or correct_value not in unique:
            return None
        rng = random.Random(_stable_seed(kind, concept, prompt, correct_value))
        rng.shuffle(unique)
        correct = unique.index(correct_value)
        key = f"{kind}:{zlib.crc32((concept + prompt).encode()):08x}"
        return Question(
            key=key,
            prompt=prompt,
            options=tuple(unique),
            correct=correct,
            explanation=explanation,
            difficulty=difficulty,
            kind=kind,
            concept=concept,
            source=_source_label(source, heading_path),
        )

    # -- acceso por dificultad -------------------------------------------
    def get(self, concept: str, difficulty: int) -> Question | None:
        cache_key = (_fold(concept), difficulty)
        if cache_key in self._cache:
            return self._cache[cache_key]
        builders = {
            1: lambda: self.cloze(concept),
            2: lambda: self.reverse(concept),
            3: lambda: self.definition(concept, close=True) or self.definition(concept, close=False),
            4: lambda: self.section_of(concept),
            5: lambda: self.truth(concept),
        }
        builder = builders.get(difficulty)
        question = builder() if builder else None
        self._cache[cache_key] = question
        return question

    def available(self, concept: str) -> list[int]:
        return [level for level in range(1, 6) if self.get(concept, level) is not None]

    def quiz(self, concepts: Sequence[str], size: int = 6) -> list[Question]:
        """Quiz variado: una pregunta por concepto, sin repetir enunciado."""
        questions: list[Question] = []
        used: set[str] = set()
        prompts: set[str] = set()
        orders = (
            (3, 2, 1, 4, 5),
            (2, 1, 3, 4, 5),
            (1, 3, 2, 4, 5),
            (4, 3, 2, 1, 5),
            (3, 1, 2, 5, 4),
            (2, 3, 1, 4, 5),
        )
        for index, concept in enumerate(concepts):
            for difficulty in orders[index % len(orders)]:
                question = self.get(concept, difficulty)
                if question is None or question.key in used or question.prompt in prompts:
                    continue
                used.add(question.key)
                prompts.add(question.prompt)
                questions.append(question)
                break
            if len(questions) >= size:
                break
        return questions


# ---------------------------------------------------------------------------
# Sondeo adaptativo (bracketing del borde de conocimiento)
# ---------------------------------------------------------------------------


@dataclass
class ProbeAnswer:
    concept: str
    difficulty: int
    question_key: str
    prompt: str
    correct: bool
    chosen: str
    expected: str
    at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


@dataclass
class Strand:
    """Un hilo de conocimiento que se sondea por separado."""

    concept: str
    reason: str
    levels: list[int] = field(default_factory=list)
    answers: list[ProbeAnswer] = field(default_factory=list)
    floor: int = 0
    ceiling: int = 6

    @property
    def bracketed(self) -> bool:
        if self.floor >= (max(self.levels) if self.levels else 5):
            return True
        return self.ceiling - self.floor <= 1

    def _remaining(self) -> list[int]:
        return [level for level in self.levels if self.floor < level < self.ceiling]

    @property
    def next_difficulty(self) -> int | None:
        remaining = self._remaining()
        if not remaining:
            return None
        if not self.answers:
            # Empieza en el nivel medio-bajo y salta fuerte si acierta.
            middle = remaining[len(remaining) // 2 - (1 if len(remaining) > 2 else 0)]
            return middle
        # Bisección dentro del intervalo aún no delimitado.
        return remaining[len(remaining) // 2]

    def record(self, answer: ProbeAnswer) -> None:
        self.answers.append(answer)
        if answer.correct:
            self.floor = max(self.floor, answer.difficulty)
        else:
            self.ceiling = min(self.ceiling, answer.difficulty)

    def level_text(self) -> str:
        if not self.answers:
            return "sin datos"
        top = max(self.levels) if self.levels else 5
        if self.floor >= top:
            return f"acierta hasta el nivel más exigente ({top})"
        if self.ceiling == 6:
            return f"acierta al menos hasta el nivel {self.floor}"
        if self.floor == 0:
            return f"su conocimiento se corta antes del nivel {self.ceiling}"
        return f"borde entre el nivel {self.floor} y el {self.ceiling}"


def choose_strands(
    bundle: MaterialBundle, factory: QuestionFactory, goal: str, limit: int = 2
) -> list[Strand]:
    """Elige los hilos que el plan va a necesitar, según la meta."""
    tokens = {token for token in re.findall(r"[a-záéíóúñ]{4,}", _fold(goal))}
    scored: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    for definition in factory.definitions:
        concept = definition.term
        key = _fold(concept)
        if key in seen:
            continue
        seen.add(key)
        score = 3 * sum(1 for token in tokens if token in key)
        score += 2 * sum(1 for token in tokens if token in _fold(definition.section))
        score += min(len(factory.sentences_with(concept)), 4)
        if definition.is_categorical:
            score += 1
        scored.append((-score, len(concept), concept))
    scored.sort()
    strands: list[Strand] = []
    for _, _, concept in scored:
        levels = factory.available(concept)
        if not levels:
            continue
        strands.append(
            Strand(
                concept=concept,
                reason=f"es una pieza central de lo que pides: «{goal}»",
                levels=levels,
            )
        )
        if len(strands) >= limit:
            break
    return strands


# ---------------------------------------------------------------------------
# Plan: nodos y mapa de dependencias
# ---------------------------------------------------------------------------


@dataclass
class TeachNode:
    id: str
    label: str
    kind: str  # 'unconditional' | 'derived' | 'goal'
    statement: str
    quote: str
    source: str
    section: str
    parent: str | None = None
    parents: list[str] = field(default_factory=list)
    concept: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "kind": self.kind,
            "statement": self.statement,
            "quote": self.quote,
            "source": self.source,
            "section": self.section,
            "parent": self.parent,
            "parents": self.parents,
            "concept": self.concept,
        }


@dataclass
class Plan:
    goal: str
    nodes: list[TeachNode]
    mermaid: str
    narrative: str
    approved: bool = False

    def node(self, node_id: str | None) -> TeachNode | None:
        if not node_id:
            return None
        return next((n for n in self.nodes if n.id == node_id), None)


def _mermaid_label(text: str, limit: int = 42) -> str:
    text = re.sub(r'["\'`{}\[\]()<>|]', "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[:limit].rstrip(" ,;:.") + "…"
    return text.replace("\n", " ")


def _mermaid(nodes: Sequence[TeachNode]) -> str:
    lines = ["graph TD"]
    ids = {node.id: f"N{index}" for index, node in enumerate(nodes)}
    for node in nodes:
        lines.append(f'    {ids[node.id]}["{_mermaid_label(node.label)}"]')
    for node in nodes:
        parents = node.parents or ([node.parent] if node.parent else [])
        for parent in parents:
            if parent in ids:
                lines.append(f"    {ids[parent]} --> {ids[node.id]}")
    for node in nodes:
        if node.kind == "unconditional":
            lines.append(f"    style {ids[node.id]} fill:#e3f2fd,stroke:#1565c0")
        elif node.kind == "goal":
            lines.append(f"    style {ids[node.id]} fill:#e8f5e9,stroke:#2e7d32")
    return "\n".join(lines)


def _goal_tokens(goal: str) -> set[str]:
    return {token for token in re.findall(r"[a-záéíóúñ]{4,}", _fold(goal))}


def build_plan(
    bundle: MaterialBundle,
    factory: QuestionFactory,
    goal: str,
    strands: Sequence[Strand],
) -> Plan:
    """Construye un plan de dependencias a partir del material real."""
    focus = [strand.concept for strand in strands]
    tokens = _goal_tokens(goal)
    focus_sections: set[str] = set()
    for concept in focus:
        for section in factory._sections_of(concept):  # noqa: SLF001 - mismo módulo
            focus_sections.add(_fold(section))

    def relevance(definition: Definition) -> int:
        score = 0
        key = _fold(definition.term)
        if any(token in key for token in tokens):
            score += 5
        section = _fold(definition.section)
        if any(token in section for token in tokens):
            score += 3
        if any(section == name or section in name for name in focus_sections):
            score += 3
        if any(_fold(concept) in key or key in _fold(concept) for concept in focus):
            score += 4
        if any(_fold(concept) in _fold(definition.body) for concept in focus):
            score += 2
        if definition.is_categorical:
            score += 1
        return score

    ranked = sorted(
        factory.definitions,
        key=lambda d: (-relevance(d), _stable_seed(d.term)),
    )

    # Raíces: verdades incondicionales relevantes para el foco.
    def concept_in(text: str) -> str:
        folded = _fold(text)
        for term in factory.term_pool:
            if len(term) >= 4 and _fold(term) in folded:
                return term
        return ""

    def truth_score(truth) -> int:
        score = 2 * truth.strength
        if any(_fold_contains(truth.text, concept) for concept in focus):
            score += 4
        if any(token in _fold(truth.text) for token in tokens):
            score += 2
        section = _fold(truth.heading_path[-1]) if truth.heading_path else ""
        if section and any(section == name or section in name for name in focus_sections):
            score += 2
        if not concept_in(truth.text):
            score -= 3
        return score

    truths = sorted(
        [truth for truth in bundle.truths if 45 <= len(truth.text) <= 200],
        key=lambda t: (-truth_score(t), _stable_seed(t.text)),
    )
    roots: list[TeachNode] = []
    for truth in truths:
        if len(roots) >= 2 or truth_score(truth) < 2:
            break
        roots.append(
            TeachNode(
                id=f"raiz{len(roots) + 1}",
                label=_trim(truth.text, 64),
                kind="unconditional",
                statement=truth.text,
                quote=truth.text,
                source=Path(truth.source).name,
                section=truth.heading_path[-1] if truth.heading_path else "",
                concept=concept_in(truth.text),
            )
        )

    nodes: list[TeachNode] = list(roots)
    root_concepts = {_fold(node.concept) for node in roots if node.concept}
    derived: list[TeachNode] = []
    for definition in ranked:
        if len(derived) >= 4:
            break
        if relevance(definition) < 2 and derived:
            break
        key = _fold(definition.term)
        if key in root_concepts:
            continue
        if any(_fold(node.label) == key for node in nodes):
            continue
        parent = roots[0].id if roots else None
        if roots:
            for root in roots:
                if root.section and _fold(root.section) == _fold(definition.section):
                    parent = root.id
                    break
        derived.append(
            TeachNode(
                id=f"nodo{len(derived) + 1}",
                label=definition.term,
                kind="derived",
                statement=f"{definition.term}: {definition.body}",
                quote=definition.sentence,
                source=Path(definition.source).name,
                section=definition.heading_path[-1] if definition.heading_path else "",
                parent=parent,
                concept=definition.term,
            )
        )
        nodes.append(derived[-1])

    if not roots and nodes:
        # Sin verdades detectadas: la definición más relevante hace de base.
        nodes[0].kind = "unconditional"
        nodes[0].parent = None

    goal_node = TeachNode(
        id="meta",
        label=goal or "Comprender el tema",
        kind="goal",
        statement=goal,
        quote="",
        source="",
        section="",
        parents=[node.id for node in nodes],
        concept=focus[0] if focus else "",
    )
    nodes.append(goal_node)

    root_labels = [f"«{node.label}»" for node in nodes if node.kind == "unconditional"]
    narrative = (
        f"La meta es **{goal or 'comprender el tema'}**. "
        + ("El plan arranca en lo que el material sostiene sin excepciones: "
           + ", ".join(root_labels) + ". " if root_labels else "")
        + f"Desde ahí sube por {len(derived)} idea(s) que dependen de esa base"
        + (f" y desemboca en «{focus[0]}»." if focus else ".")
        + " El orden del mapa es el orden en que se enseña."
    )
    return Plan(goal=goal, nodes=nodes, mermaid=_mermaid(nodes), narrative=narrative)


# ---------------------------------------------------------------------------
# Lección: motivar → establecer → conectar → comprobar
# ---------------------------------------------------------------------------


@dataclass
class LessonStep:
    """El texto de enseñanza de un nodo."""

    node_id: str
    motivate: str
    establish: str
    connect: str
    question: Question | None
    source: str


class Teacher:
    """Produce el texto de cada nodo. Sin IA usa el propio material."""

    def __init__(self, bundle: MaterialBundle, plan: Plan, factory: QuestionFactory) -> None:
        self.bundle = bundle
        self.plan = plan
        self.factory = factory

    def step(self, node: TeachNode) -> LessonStep:
        parent = self.plan.node(node.parent)
        if node.kind == "unconditional":
            motivate = (
                "Antes de añadir nada, fijamos una afirmación que el material sostiene "
                "sin excepciones. No necesita matices, así que se acepta tal cual y "
                "sirve de suelo firme para todo lo que viene después."
            )
            establish = node.statement
        elif node.kind == "goal":
            motivate = (
                "Esta es la meta. Ya tienes las piezas y sus enlaces: el último paso es "
                "ver el conjunto como una sola idea, no como una lista."
            )
            establish = self._goal_summary()
        else:
            anchor = f"«{parent.label}»" if parent else "la base anterior"
            motivate = (
                f"Con {anchor} ya fijado, aparece «{node.label}». El material lo presenta "
                f"después porque depende de ello: sin lo anterior no podrías explicar por "
                f"qué «{node.label}» es como es."
            )
            establish = node.statement

        return LessonStep(
            node_id=node.id,
            motivate=motivate,
            establish=establish,
            connect=self._connect_text(node, parent),
            question=self._question_for(node),
            source=node.source,
        )

    def _goal_summary(self) -> str:
        derived = [node for node in self.plan.nodes if node.kind == "derived"]
        if not derived:
            return self.plan.goal
        lines = [f"- **{node.label}** — {_trim(node.statement, 140)}" for node in derived]
        return (
            f"Todo lo anterior se comprime en esto: **{self.plan.goal}**.\n\n"
            + "\n".join(lines)
        )

    def _connect_text(self, node: TeachNode, parent: TeachNode | None) -> str:
        if node.kind == "goal":
            return (
                "Cada idea anterior apunta aquí: la meta es el nodo donde se juntan "
                "todas las dependencias."
            )
        if parent is None:
            return "Es la raíz del mapa: de aquí cuelga todo lo demás."
        shared = self._shared_sentence(parent.concept or parent.label, node.concept or node.label)
        base = f"«{parent.label}» → «{node.label}»: el nodo nuevo cuelga del anterior."
        if shared:
            return f"{base}\n\nEl material los une en una misma idea:\n\n> «{_trim(shared, 220)}»"
        section = node.section or parent.section
        if section:
            return f"{base} Ambos se desarrollan en «{section}»."
        return base

    def _shared_sentence(self, first: str, second: str) -> str | None:
        if not first or not second or first == second:
            return None
        first_key, second_key = _fold(first), _fold(second)
        for paragraph in self.bundle.paragraphs:
            folded = _fold(paragraph.text)
            if first_key in folded and second_key in folded:
                for sentence in split_sentences(paragraph.text):
                    inner = _fold(sentence)
                    if first_key in inner and second_key in inner:
                        return _clean_sentence(sentence)
        return None

    def _question_for(self, node: TeachNode) -> Question | None:
        concept = node.concept or node.label
        if node.kind == "goal":
            return self.factory.get("", 5)
        if node.kind == "unconditional":
            # La raíz es una afirmación universal: se comprueba con el concepto
            # que menciona, no con otra pregunta genérica igual para todas.
            for term in self.factory.term_pool:
                if len(term) >= 4 and _fold(term) in _fold(node.statement):
                    concept = term
                    break
        for difficulty in (3, 2, 5, 1, 4):
            question = self.factory.get(concept, difficulty)
            if question is not None:
                return question
        return None


# ---------------------------------------------------------------------------
# Sesión: estado, registro y persistencia
# ---------------------------------------------------------------------------


@dataclass
class NodeProgress:
    node_id: str
    status: str = "pendiente"  # pendiente | superado | flojo
    attempts: int = 0
    notes: str = ""


@dataclass
class LearningSession:
    materia: str
    goal: str
    session_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    created: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    plan: Plan | None = None
    strands: list[Strand] = field(default_factory=list)
    progress: dict[str, NodeProgress] = field(default_factory=dict)
    phase: str = "meta"  # meta | sondeo | plan | leccion | cierre
    current_index: int = 0
    ai_mode: str = "local"
    log: list[str] = field(default_factory=list)

    # -- registro ---------------------------------------------------------
    def note(self, text: str) -> None:
        self.log.append(f"{datetime.now().strftime('%H:%M')} — {text}")

    def progress_for(self, node_id: str) -> NodeProgress:
        if node_id not in self.progress:
            self.progress[node_id] = NodeProgress(node_id=node_id)
        return self.progress[node_id]

    @property
    def completed_nodes(self) -> int:
        return sum(1 for item in self.progress.values() if item.status in {"superado", "flojo"})

    def total_nodes(self) -> int:
        return len(self.plan.nodes) if self.plan else 0

    def probe_summary(self) -> str:
        if not self.strands:
            return "Sin sondeo."
        lines = []
        for strand in self.strands:
            hits = sum(1 for answer in strand.answers if answer.correct)
            lines.append(
                f"- **{strand.concept}**: {hits}/{len(strand.answers)} aciertos — {strand.level_text()}"
            )
        return "\n".join(lines)

    def weak_concepts(self) -> list[str]:
        weak: list[str] = []
        for strand in self.strands:
            if any(not answer.correct for answer in strand.answers):
                weak.append(strand.concept)
        if self.plan:
            for node_id, item in self.progress.items():
                node = self.plan.node(node_id)
                if item.status == "flojo" and node and node.concept:
                    weak.append(node.concept)
        return list(dict.fromkeys(weak))

    # -- persistencia -----------------------------------------------------
    def to_markdown(self) -> str:
        lines = [
            "---",
            f'materia: "{self.materia}"',
            f'meta: "{self.goal}"',
            f'fecha: "{self.created}"',
            f'session_id: "{self.session_id}"',
            f"motor: {self.ai_mode}",
            "---",
            "",
            f"# Sesión de aprendizaje: {self.goal}",
            "",
            f"**Materia:** {self.materia}  ",
            f"**Inicio:** {self.created}  ",
            f"**Modo:** {'con IA de apoyo' if self.ai_mode == 'ia' else 'local (sin IA)'}",
            "",
            "## Sondeo inicial",
            "",
            self.probe_summary(),
            "",
        ]
        if self.plan:
            lines += ["## Mapa de dependencias", "", "```mermaid", self.plan.mermaid, "```", ""]
            lines += ["## Nodos", ""]
            for node in self.plan.nodes:
                status = self.progress.get(node.id)
                mark = status.status if status else "pendiente"
                lines.append(f"### {node.label}  ({mark})")
                lines.append("")
                lines.append(node.statement)
                if node.quote and node.quote != node.statement:
                    lines.append("")
                    lines.append(f"> {node.quote}")
                if node.source:
                    lines.append("")
                    lines.append(f"*Fuente: {node.source}*")
                if status and status.notes:
                    lines.append("")
                    lines.append(status.notes)
                lines.append("")
        weak = self.weak_concepts()
        lines += ["## Para repasar", ""]
        lines += [f"- {concept}" for concept in weak] or ["- (nada pendiente)"]
        lines += ["", "## Bitácora", ""]
        lines += [f"- {entry}" for entry in self.log] or ["- (sin eventos)"]
        lines.append("")
        return "\n".join(lines)

    def filename(self) -> str:
        base = f"{self.materia}_{self.goal}_{self.session_id}"
        base = re.sub(r"[^\w\-ÁÉÍÓÚÜÑáéíóúüñ]+", "_", base)
        return base[:120] + ".md"

    def save(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / self.filename()
        path.write_text(self.to_markdown(), encoding="utf-8")
        return path


def _session_metadata(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    meta: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip('"')
    return meta


def list_sessions(directory: Path) -> list[dict]:
    entries: list[dict] = []
    if not directory.is_dir():
        return entries
    for path in sorted(directory.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        meta = _session_metadata(text)
        body = text.split("---", 2)[-1]
        body = re.sub(r"^#.*$", "", body, count=1, flags=re.M).strip()
        entries.append(
            {
                "path": path,
                "name": path.name,
                "materia": meta.get("materia", ""),
                "meta": meta.get("meta", meta.get("tema", "")),
                "fecha": meta.get("fecha", ""),
                "motor": meta.get("motor", ""),
                "preview": _trim(body, 260),
                "content": text,
            }
        )
    return entries


# ---------------------------------------------------------------------------
# Utilidades de apoyo didáctico
# ---------------------------------------------------------------------------

def contrast_pairs(bundle: MaterialBundle, limit: int = 6) -> list[tuple[str, str, str]]:
    """Pares de conceptos que el material presenta juntos (para contrastar)."""
    pairs: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str]] = set()
    by_key = {_fold(definition.term): definition.term for definition in bundle.definitions}
    for paragraph in bundle.paragraphs:
        folded = _fold(paragraph.text)
        present = [term for key, term in by_key.items() if key in folded]
        for index, first in enumerate(present):
            for second in present[index + 1:]:
                key = tuple(sorted((_fold(first), _fold(second))))
                if first == second or key in seen:
                    continue
                seen.add(key)
                pairs.append((first, second, _trim(paragraph.text, 180)))
        if len(pairs) >= limit * 2:
            break
    return pairs[:limit]


def material_score(bundle: MaterialBundle) -> int:
    """Cuánta materia prima hay para enseñar (para avisar antes de empezar)."""
    return len(bundle.definitions) * 3 + len(bundle.truths) + len(bundle.paragraphs) // 20
