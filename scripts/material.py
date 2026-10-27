#!/usr/bin/env python3
"""
Carga y normalización del material de estudio.

El material de una materia puede vivir en tres sitios distintos y en dos
formatos distintos (prosa limpia o Markdown generado por pandoc/calibre):

    materias/<materia>/libro_principal.md      (a veces sólo un placeholder)
    materias/<materia>/salidas/*.md
    salidas/<materia>/*.md                     (aquí cae la conversión de EPUB)

Este módulo es el único sitio que interpreta esos bytes. Devuelve párrafos
reconstruidos, definiciones, afirmaciones universales y secciones, de modo que
el resto de la aplicación nunca vuelva a mirar el Markdown crudo.
"""

from __future__ import annotations

import math
import pathlib
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Iterable, Sequence

from config import MATERIAS_DIR, SALIDAS_DIR, get_materia_dir

# ---------------------------------------------------------------------------
# Modelo de datos
# ---------------------------------------------------------------------------

KIND_LABELS = {
    "libro": "Libro principal",
    "guia": "Guía de aprendizaje",
    "memoria": "Memoria de la materia",
    "fuentes": "Fuentes usadas",
    "salida": "Material convertido",
}


@dataclass(frozen=True)
class Paragraph:
    """Un párrafo reconstruido con la ruta de encabezados donde vive."""

    text: str
    source: str
    heading_path: tuple[str, ...] = ()

    @property
    def section(self) -> str:
        return self.heading_path[-1] if self.heading_path else ""


@dataclass(frozen=True)
class Definition:
    """Una definición explícita encontrada en el material."""

    term: str
    body: str
    sentence: str
    source: str
    heading_path: tuple[str, ...] = ()

    @property
    def section(self) -> str:
        return self.heading_path[-1] if self.heading_path else ""

    @property
    def is_categorical(self) -> bool:
        """El predicado nombra una categoría («un patrón…», «la capacidad…»)."""
        return bool(_DEF_CATEGORY_START.match(self.body))


@dataclass(frozen=True)
class Truth:
    """Afirmación sin matices: se acepta tal cual, sin excepciones."""

    text: str
    source: str
    heading_path: tuple[str, ...] = ()

    @property
    def section(self) -> str:
        return self.heading_path[-1] if self.heading_path else ""

    @property
    def strength(self) -> int:
        """Cuánto se parece a una verdad incondicional fuerte (0-3)."""
        folded = _fold(self.text)
        score = 0
        if re.search(r"\b(todos los|todas las|ningun|ninguna|nunca|jamas)\b", folded):
            score += 2
        if re.search(r"\bsiempre\b", folded):
            score += 1
        if re.search(r"\b(en el otro|en este caso|en este ejemplo|aqui|alli|esto)\b", folded):
            score -= 1
        return max(0, score)


@dataclass(frozen=True)
class Section:
    title: str
    level: int
    source: str
    chars: int


@dataclass
class MaterialBundle:
    """Todo el material utilizable de una materia, ya interpretado."""

    materia: str
    paragraphs: list[Paragraph] = field(default_factory=list)
    definitions: list[Definition] = field(default_factory=list)
    truths: list[Truth] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    concepts: list[str] = field(default_factory=list)
    sources: list[tuple[str, str, int]] = field(default_factory=list)
    total_chars: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def has_content(self) -> bool:
        return bool(self.paragraphs) and self.total_chars >= 800

    def quality(self) -> tuple[str, str]:
        """Devuelve (nivel, explicación) sobre lo aprovechable del material."""
        if not self.has_content:
            return (
                "insuficiente",
                "No hay prosa suficiente. Importa el libro (PDF/EPUB → Markdown) "
                "o convierte el EPUB desde esta misma aplicación.",
            )
        if len(self.definitions) >= 8 and len(self.truths) >= 3:
            return (
                "bueno",
                f"{len(self.paragraphs)} párrafos, {len(self.definitions)} definiciones "
                f"y {len(self.truths)} afirmaciones universales.",
            )
        if len(self.definitions) >= 3:
            return (
                "aceptable",
                f"{len(self.paragraphs)} párrafos y {len(self.definitions)} definiciones. "
                "Con más texto las preguntas serían más variadas.",
            )
        return (
            "limitado",
            f"{len(self.paragraphs)} párrafos, sin definiciones claras. "
            "Se generarán preguntas de completar y de relación entre secciones.",
        )

    def related(self, query: str, limit: int = 6) -> list[Paragraph]:
        """Párrafos más relevantes para una consulta (búsqueda léxica simple)."""
        tokens = _content_tokens(query)
        if not tokens:
            return self.paragraphs[:limit]
        scored: list[tuple[float, int, Paragraph]] = []
        for idx, par in enumerate(self.paragraphs):
            hay = _fold(par.text)
            score = sum(hay.count(tok) for tok in tokens)
            if score:
                # Normaliza por longitud para no premiar sólo párrafos enormes.
                scored.append((score / math.sqrt(len(par.text) + 40), idx, par))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [item[2] for item in scored[:limit]]


# ---------------------------------------------------------------------------
# Limpieza de Markdown generado por pandoc / calibre
# ---------------------------------------------------------------------------

_RE_SVG = re.compile(r"<svg\b.*?</svg>", re.S | re.I)
_RE_IMG = re.compile(r"!\[[^\]]*\]\([^)]*\)(?:\{[^}]*\})?")
_RE_EMPTY_ANCHOR = re.compile(r"\[\]\{[^}]*\}")
_RE_BRACKET_ATTR = re.compile(r"\[([^\[\]]*)\]\{[^}]*\}")
_RE_CODE_ATTR = re.compile(r"`([^`]*)`\{=[^}]*\}")
_RE_FENCE = re.compile(r"^[ \t]*:::+[^\n]*$", re.M)
_RE_HEADING_ATTR = re.compile(r"^([ \t]{0,3}#{1,6}[^\n{]*?)[ \t]*\{[^}\n]*\}[ \t]*$", re.M)
_RE_HTML = re.compile(r"<[^>\n]{0,300}>")
_RE_ESCAPE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!|>~])")
_RE_PAGE_LINE = re.compile(
    r"^[ \t]*(?:\[?\s*(?:p[áa]g(?:ina)?\.?\s*)?\d{1,4}\s*\]?"
    r"|\[?(?:I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII)\]?"
    r"|P\s*A\s*R\s*T\s*E"
    r"|.*\bPage\s+\d+[ \t]*"
    r"|.*\bdoc\s+\d{2}/\d{2}/\d{2}\b.*)[ \t]*$",
    re.I,
)
_RE_NUMBERED = re.compile(r"^\s*(?:\d{1,2}[.)]|[-*•–—])\s+")
_RE_CAPS_PREFIX = re.compile(
    r"^((?:[A-ZÁÉÍÓÚÑ]{2,}\s+){2,})(?=[A-ZÁÉÍÓÚÑ][a-záéíóúñ])"
)
_RE_SENT_END = re.compile(r"[.!?…:;»”\"')\]]\s*$")
_RE_STARTS_UPPER = re.compile(r"^[¿¡\"«“(\[A-ZÁÉÍÓÚÑ0-9]")
_RE_WORD = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{4,}")
_RE_MULTISPACE = re.compile(r"[ \t]{2,}")


def _fold(text: str) -> str:
    """Minúsculas sin acentos, para comparar y buscar."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def _content_tokens(text: str) -> list[str]:
    stop = {
        "para", "como", "este", "esta", "esto", "esos", "esas", "sobre", "entre",
        "desde", "hasta", "cuando", "donde", "porque", "aunque", "tambien", "sino",
        "todo", "todos", "toda", "todas", "hace", "puede", "pueden", "sido", "tiene",
        "tienen", "desde", "mismo", "misma", "otras", "otros", "cada", "segun",
    }
    seen: list[str] = []
    for tok in _fold(text).split():
        tok = "".join(ch for ch in tok if ch.isalnum())
        if len(tok) < 4 or tok in stop or tok.isdigit():
            continue
        if tok not in seen:
            seen.append(tok)
    return seen


def clean_markdown(raw: str) -> str:
    """Quita los artefactos de pandoc/calibre y deja prosa legible."""
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = _RE_SVG.sub("", text)
    text = _RE_IMG.sub("", text)
    text = _RE_EMPTY_ANCHOR.sub("", text)
    for _ in range(4):
        text, replaced = _RE_BRACKET_ATTR.subn(r"\1", text)
        if not replaced:
            break
    text = _RE_CODE_ATTR.sub(r"\1", text)
    text = _RE_FENCE.sub("", text)
    text = _RE_HEADING_ATTR.sub(r"\1", text)
    # Los saltos de línea dentro de una etiqueta HTML se consideran espacio.
    text = _RE_HTML.sub("", text)
    text = _RE_ESCAPE.sub(r"\1", text)
    text = text.replace("\u00a0", " ").replace("\u00ad", "")
    return text


def _vocabulary(lines: Sequence[str]) -> set[str]:
    vocab: set[str] = set()
    for line in lines:
        for word in _RE_WORD.findall(_fold(line)):
            vocab.add(word)
    return vocab


def _join_hyphen(left: str, right: str, vocab: set[str]) -> str:
    """Une una palabra cortada por guión de fin de línea.

    Si el guión es legítimo (``teórico-práctico``) se conserva cuando la forma
    con guión existe en el propio texto y la unida no.
    """
    head = left.rstrip()
    if not head.endswith("-") or not right or not right[0].islower():
        return f"{left} {right}"
    prefix = re.search(r"([A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)-$", head)
    next_word = re.match(r"([A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)", right)
    if not prefix or not next_word:
        return f"{left} {right}"
    joined = prefix.group(1) + next_word.group(1)
    hyphenated = f"{prefix.group(1)}-{next_word.group(1)}"
    if _fold(hyphenated) in vocab and _fold(joined) not in vocab:
        return f"{left} {right}"
    return head[:-1] + right


def _next_nonblank(lines: Sequence[str], start: int) -> str:
    for line in lines[start:]:
        if line.strip():
            return line.strip()
    return ""


def rebuild_blocks(cleaned: str, vocab: set[str] | None = None) -> list[str]:
    """Reconstruye párrafos a partir de líneas partidas por el PDF.

    El texto convertido suele traer una línea por renglón e incluso una línea
    en blanco entre renglones. Se vuelve a unir mientras la frase no haya
    terminado.
    """
    lines = cleaned.split("\n")
    if vocab is None:
        vocab = _vocabulary(lines)

    blocks: list[str] = []
    buffer: list[str] = []

    def flush() -> None:
        if not buffer:
            return
        paragraph = _RE_MULTISPACE.sub(" ", " ".join(buffer)).strip()
        if paragraph:
            blocks.append(paragraph)
        buffer.clear()

    for index, raw_line in enumerate(lines):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            flush()
            blocks.append(line)
            continue
        if _RE_PAGE_LINE.match(line):
            continue
        if _RE_NUMBERED.match(line):
            # Un elemento de lista no se pega al párrafo anterior.
            flush()
            buffer.append(line)
            continue
        if buffer:
            previous = buffer[-1]
            next_line = _next_nonblank(lines, index + 1) if _RE_SENT_END.search(previous) else ""
            long_enough = len(" ".join(buffer)) > 60
            sentence_done = bool(_RE_SENT_END.search(previous))
            next_is_new = bool(next_line) and bool(_RE_STARTS_UPPER.match(next_line))
            if sentence_done and long_enough and next_is_new:
                flush()
            else:
                buffer[-1] = _join_hyphen(previous, line, vocab)
                continue
        buffer.append(line)
    flush()

    # Une elementos de lista consecutivos que quedaron como bloques sueltos.
    return _strip_residual_noise(blocks)


def _strip_residual_noise(blocks: Iterable[str]) -> list[str]:
    out: list[str] = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if block.startswith("#"):
            out.append(block)
            continue
        if len(block) < 3:
            continue
        # Bloques que sólo son restos de maquetación.
        if re.fullmatch(r"[\W_]+", block):
            continue
        out.append(block)
    return out


# ---------------------------------------------------------------------------
# Segmentación en frases
# ---------------------------------------------------------------------------

_RE_SENT_SPLIT = re.compile(r"(?<=[.!?…])\s+(?=[¿¡\"«“(\[A-ZÁÉÍÓÚÑ0-9])")
# Punto que no termina la frase: títulos, unidades con número e iniciales.
_RE_ABBREV_PROTECT = re.compile(
    r"\b(?:Dr|Dra|Sr|Sra|Prof|Profa|Ud|Uds|Lcdo|Lcda|Ing|Lic|etc|vs|cfr)\.(?=\s+[A-ZÁÉÍÓÚÑ])"
    r"|\b(?:p|pp|vol|núm|num|cap|caps|fig|tab|art|aprox|ed)\.(?=\s*\d)"
    r"|\bet al\."
    r"|\b[A-ZÁÉÍÓÚÑ]\.(?=\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ])",
)
_MARK = "\u2024"


def split_sentences(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    protected = _RE_ABBREV_PROTECT.sub(
        lambda match: match.group(0).replace(".", _MARK), text
    )
    pieces = _RE_SENT_SPLIT.split(protected)
    return [piece.replace(_MARK, ".").strip() for piece in pieces if piece.strip()]


# ---------------------------------------------------------------------------
# Extracción de conocimiento
# ---------------------------------------------------------------------------

_TERM_STOPWORDS = {
    "este", "esta", "esto", "estos", "estas", "ese", "esa", "eso", "esos", "esas",
    "aquel", "aquella", "por", "para", "cuando", "como", "pero", "sin", "con",
    "en", "el", "la", "los", "las", "un", "una", "unos", "unas", "su", "sus",
    "que", "se", "lo", "le", "les", "nos", "hay", "había", "ser", "estar",
}
_DEF_EXPLICIT = (
    r"(?:se define como|se refiere a|consiste en|se entiende como|se entiende por|"
    r"es definid[oa] como|se conceptualiza como|abarca|designa|significa)"
)
_DEF_COPULA = r"(?:es|son)"
# Un predicado de definición empieza nombrando la categoría a la que pertenece
# el término ("un patrón...", "la capacidad..."), no evaluándolo ("demasiado
# inusual..."). Esto separa definiciones de meras opiniones del autor.
_DEF_CATEGORY = (
    r"(?:un|una|unos|unas|el|la|los|las|aquel|aquella|conjunto|proceso|patr[óo]n|"
    r"sistema|t[ée]cnica|teor[íi]a|modelo|m[ée]todo|enfoque|estudio|capacidad|"
    r"tendencia|caracter[íi]stica|forma|tipo|clase|modo|mecanismo|estructura|"
    r"funci[óo]n|principio|concepto|t[ée]rmino|disciplina|escuela|concepci[óo]n|"
    r"supuesto|hip[óo]tesis|trastorno|s[íi]ndrome|terapia|instrumento|prueba|"
    r"escala|rasgo|estado|conducta|emoci[óo]n|cognici[óo]n|procedimiento|"
    r"secuencia|relaci[óo]n|variable|constructo|paradigma|postulado|fen[óo]meno|"
    r"s[íi]ntoma|criterio|diagn[óo]stico|tratamiento|resultado|efecto|"
    r"interpretaci[óo]n|clasificaci[óo]n|etapa|fase|nivel|componente|elemento)"
)
_DEF_CATEGORY_START = re.compile(r"^(?:" + _DEF_CATEGORY + r")\b", re.I)
_DEF_PATTERNS = (
    re.compile(
        r"^(?:El|La|Los|Las|Un|Una|Unos|Unas)\s+(?P<term>[^,.;:()]{2,58}?)\s+"
        + _DEF_COPULA
        + r"\s+(?P<body>" + _DEF_CATEGORY + r"\b.{20,320})$",
        re.I,
    ),
    re.compile(
        r"^(?:El|La|Los|Las|Un|Una|Unos|Unas)\s+(?P<term>[^,.;:()]{2,58}?)\s+"
        + _DEF_EXPLICIT
        + r"\s+(?P<body>.{25,320})$",
        re.I,
    ),
    re.compile(
        r"^(?P<term>[A-ZÁÉÍÓÚÑ][^,.;:()]{2,48}?)\s+" + _DEF_EXPLICIT + r"\s+(?P<body>.{20,320})$",
        re.I,
    ),
    re.compile(
        r"^(?:Se entiende por|Se define como|Se denomina|Llamamos)\s+"
        r"(?P<term>[^,.;:()]{2,48}?)\s+(?:a|al|como|la|el)\s+(?P<body>.{20,320})$",
        re.I,
    ),
    re.compile(r"^\*\*(?P<term>[^*]{2,48})\*\*[:.]\s*(?P<body>.{25,320})$"),
)

# Palabras con las que no puede empezar el término de una definición: son
# arranques de oración (verbos conjugados, conectores, cuantificadores), no
# nombres de concepto.
_TERM_BAD_START = {
    "asumimos", "creemos", "sospecho", "pienso", "considero", "vemos", "sabemos",
    "existe", "existen", "hay", "tiene", "tienen", "puede", "pueden", "debe",
    "deben", "fue", "fueron", "era", "eran", "es", "son", "esta", "está",
    "están", "ha", "han", "había", "hemos", "nunca", "siempre", "aunque",
    "quienes", "quien", "quién", "otros", "otras", "algunos", "algunas",
    "muchos", "muchas", "todo", "todos", "toda", "todas", "ningún", "ninguna",
    "cada", "según", "mientras", "aun", "aún", "también", "además", "así",
    "luego", "después", "antes", "ahora", "aquí", "allí", "esto", "ello",
    "cómo", "como", "qué", "que", "cuál", "cual", "cuándo", "cuando", "dónde",
    "donde", "quién", "quien", "por",
}

_TERM_TRAILING_ADVERBS = {
    "también", "tambien", "además", "ademas", "sólo", "solo", "aún", "aun",
    "siempre", "nunca", "ya", "así", "asi", "muy", "más", "mas", "menos",
    "tanto", "cuanto", "bien", "mal", "aquí", "allí", "ahora", "luego",
}

_UNIVERSAL_CUE = re.compile(
    r"\b(todos los|todas las|ningún|ninguna|ninguno|siempre|nunca|jamás|"
    r"todo ser humano|en todos los casos|cada vez que|cada uno|la totalidad|"
    r"todo comportamiento|toda conducta)\b",
    re.I,
)
_HEDGE_CUE = re.compile(
    r"\b(algunos|algunas|a veces|puede|pueden|podría|podrían|suele|suelen|"
    r"tiende|tienden|generalmente|a menudo|en ocasiones|probablemente|"
    r"parece|parecen|quizá|tal vez|frecuentemente|la mayoría)\b",
    re.I,
)
_RE_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_RE_BOLD_HEADING = re.compile(r"^\*\*([^*]{2,88})\*\*[:.]?$")
_RE_CHAPTER_MARK = re.compile(r"^C\s*A\s*P\s*[IÍ]\s*T\s*U\s*L\s*O$", re.I)
_RE_ROMAN_OR_NUM = re.compile(r"^(?:[IVXLCDM]+|\d+|[a-z])$", re.I)
_RE_BOILERPLATE = re.compile(
    r"(derechos reservados|todos los derechos|marca registrada|copyright|"
    r"ISBN|impreso en|printed in|prohibida (?:su|la) reproducci|"
    r"traducci[óo]n autorizada|reservados todos|http|www\.|@|"
    r"editorial|pearson educaci|registro p[úu]blico)",
    re.I,
)
_SECTION_STOPWORDS = {
    "contenido", "resumen de contenido", "prefacio", "indice", "índice",
    "parte", "capítulo", "capitulo", "referencias", "notas", "glosario",
    "apéndice", "apendice", "bibliografía", "bibliografia",
}
# Secciones que existen en el libro pero no enseñan nada: se usan como
# separadores (para dejar de leer) en vez de como contenido.
_NOISE_SECTIONS = _SECTION_STOPWORDS | {
    "prólogo", "prologo", "agradecimientos", "dedicatoria", "créditos",
    "creditos", "portada", "cubierta", "contraportada", "acerca del autor",
    "acerca de los autores", "lecturas sugeridas", "preguntas de estudio",
    "resumen", "resúmenes", "sinopsis",
}


def _clean_term(term: str) -> str | None:
    term = _RE_MULTISPACE.sub(" ", term).strip(" \t.,;:()[]{}\"'«»")
    term = re.sub(r"[*_`]+", "", term).strip()
    term = re.sub(r"^(?:el\s+)?t[ée]rmino\s+", "", term, flags=re.I).strip()
    if not term or len(term) < 3 or len(term) > 70:
        return None
    words = term.split()
    # Un rótulo en versalitas seguido de prosa («AMOR La tarea del amor») se
    # pegó al párrafo: el rótulo no forma parte del término.
    if len(words) > 1 and words[0].isupper() and len(words[0]) >= 3:
        term = " ".join(words[1:])
        words = term.split()
    if not 1 <= len(words) <= 6:
        return None
    if words[0].lower() in _TERM_STOPWORDS or words[0].lower() in _TERM_BAD_START:
        return None
    if " que " in f" {term.lower()} ":
        return None
    if _RE_ROMAN_OR_NUM.match(term):
        return None
    if term.lower() in _SECTION_STOPWORDS:
        return None
    # Una preposición o conjunción suelta al final indica que el término se
    # cortó; pero «atención sostenida» o «desarrollo» acaban en vocal y son
    # válidos, así que se compara la última palabra completa, no el sufijo.
    if words[-1].lower() in {"que", "de", "del", "en", "y", "o", "a", "con", "por", "para", "su", "la", "el"}:
        return None
    if words[-1].lower() in _TERM_TRAILING_ADVERBS:
        return None
    if _RE_BOILERPLATE.search(term):
        return None
    if len(words) > 1 and len(words[-1]) == 1 and words[-1].isalpha():
        return None
    if not re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{3}", term):
        return None
    return term


def _clean_body(body: str) -> str | None:
    body = _RE_MULTISPACE.sub(" ", body).strip(" \t")
    if len(body) < 25 or len(body) > 320:
        return None
    if body.lower().startswith(("que ", "cómo ", "como ", "si ")):
        return None
    if len(body.split()) < 5:
        return None
    if _RE_BOILERPLATE.search(body):
        return None
    return body.rstrip(" ,;") + ("" if body.rstrip().endswith((".", "!", "?")) else ".")


def _normalise_key(term: str) -> str:
    return _fold(term).strip()


def _looks_monospaced(text: str) -> bool:
    """Detecta rótulos con letras espaciadas ('S i n o p s i s')."""
    words = text.split()
    if len(words) < 4:
        return False
    single = sum(1 for word in words if len(word) == 1 and word.isalpha())
    return single / len(words) > 0.5


def _looks_like_toc(text: str) -> bool:
    """Descarta entradas de índice: frase corta que termina en número de página."""
    stripped = text.strip()
    if len(stripped) > 110 or not re.search(r"\s\d{1,3}$", stripped):
        return False
    return not stripped.endswith((".", "?", "!"))


def _title_text(raw: str) -> str | None:
    """Texto de un encabezado, sin decidir todavía si sirve como sección."""
    title = re.sub(r"[*_`]+", "", raw)
    title = re.sub(r"\s{2,}", " ", title).strip(" .:—-")
    if not title or len(title) < 3 or len(title) > 90:
        return None
    if _RE_ROMAN_OR_NUM.match(title):
        return None
    if _looks_monospaced(title):
        return None
    if len(title.split()) > 14:
        return None
    return title


def _section_title(raw: str, *, bold: bool = False) -> str | None:
    title = _title_text(raw)
    if title is None:
        return None
    if _fold(title).strip() in _SECTION_STOPWORDS:
        return None
    if bold:
        # Un rótulo en negrita es título si arranca en mayúscula y no parece
        # el final de una palabra cortada por el PDF.
        if not title[0].isupper() or title.endswith("-") or title[0] in "¿¡":
            return None
    return title


def _chapter_title(lines: Sequence[str], start: int) -> tuple[str, int] | None:
    """Lee el número y el título que siguen a una marca 'C A P Í T U L O'."""
    collected: list[str] = []
    number = ""
    consumed = 0
    for offset in range(start + 1, min(start + 14, len(lines))):
        line = lines[offset].strip()
        if not line:
            continue
        consumed = offset - start
        bare = re.sub(r"[*_`]+", "", line).strip()
        if not number and re.fullmatch(r"\d{1,2}", bare):
            number = bare
            continue
        if _looks_monospaced(bare) or _looks_like_toc(bare) or _RE_PAGE_LINE.match(bare):
            continue
        if len(bare) < 3 or len(bare) > 70 or bare.endswith((".", ",", ";", ":")):
            if collected:
                break
            continue
        if not re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúñ]{3}", bare):
            if collected:
                break
            continue
        candidate = " ".join(collected + [bare]) if collected else bare
        if len(candidate) > 75:
            break
        collected.append(bare)
        if len(collected) >= 2:
            break
    if not collected:
        return None
    title = ": ".join(collected) if len(collected) == 2 and collected[1][0].isupper() else " ".join(collected)
    label = f"Capítulo {number}: {title}" if number else f"Capítulo: {title}"
    return label, consumed


def build_bundle(materia: str, documents: Sequence[tuple[str, str, str]]) -> MaterialBundle:
    """Construye el paquete de material.

    ``documents`` son tuplas ``(ruta, tipo, contenido_crudo)``.
    """
    bundle = MaterialBundle(materia=materia)
    definitions: dict[str, Definition] = {}
    truths: dict[str, Truth] = {}
    concepts: list[str] = []
    seen_concepts: set[str] = set()

    def remember(paragraph: Paragraph) -> None:
        bundle.paragraphs.append(paragraph)
        for sentence in split_sentences(paragraph.text):
            for definition in _definitions_from_sentence(sentence, paragraph):
                key = _normalise_key(definition.term)
                previous = definitions.get(key)
                if previous is None or len(definition.body) > len(previous.body):
                    definitions[key] = definition
                if definition.term not in seen_concepts:
                    seen_concepts.add(definition.term)
                    concepts.append(definition.term)
            truth = _truth_from_sentence(sentence, paragraph)
            if truth is not None:
                truths.setdefault(_normalise_key(truth.text[:80]), truth)

    for path, kind, raw in documents:
        cleaned = clean_markdown(raw)
        bundle.total_chars += len(cleaned)
        bundle.sources.append((path, kind, len(cleaned)))
        if len(cleaned.strip()) < 400:
            bundle.notes.append(
                f"{pathlib.Path(path).name}: {KIND_LABELS.get(kind, kind)} sin texto útil "
                f"({len(cleaned.strip())} caracteres)."
            )
            continue

        lines = cleaned.split("\n")
        vocab = _vocabulary(lines)
        stack: list[tuple[int, str]] = []
        buffer: list[str] = []
        skip_until = -1

        # Si el libro trae marcas de capítulo, todo lo anterior al primero es
        # portada, créditos e índice: no enseña nada y ensucia las secciones.
        has_chapters = any(
            _RE_CHAPTER_MARK.match(
                re.sub(r"[*_`]+", "", line).replace(" ", "")
            )
            for line in lines
            if line.strip().startswith("**")
        )
        front_matter = has_chapters
        muted = has_chapters

        def push(level: int, title: str) -> None:
            nonlocal stack
            stack = [(lvl, name) for lvl, name in stack if lvl < level]
            stack.append((level, title))
            bundle.sections.append(Section(title=title, level=level, source=path, chars=0))

        def open_heading(level: int, raw: str, *, bold: bool = False) -> bool:
            """Abre una sección. Devuelve True si la línea era un encabezado."""
            nonlocal muted, front_matter
            title = _title_text(raw)
            if title is None:
                return False
            if front_matter:
                return True
            if bold and (not title[0].isupper() or title.endswith("-") or title[0] in "¿¡"):
                return False
            if _fold(title).strip() in _NOISE_SECTIONS:
                # Sigue siendo un límite: deja de acumular contenido útil.
                muted = True
                return True
            muted = False
            push(level, title)
            return True

        def flush() -> None:
            if not buffer:
                return
            text = _RE_MULTISPACE.sub(" ", " ".join(buffer)).strip()
            buffer.clear()
            if muted:
                return
            # Un rótulo en versalitas que quedó pegado al párrafo no es prosa.
            text = _RE_CAPS_PREFIX.sub("", text).strip()
            if len(text) < 40 or not re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", text):
                return
            if _looks_monospaced(text) or _looks_like_toc(text):
                return
            remember(Paragraph(text=text, source=path,
                               heading_path=tuple(t for _, t in stack)))

        for index, raw_line in enumerate(lines):
            if index <= skip_until:
                continue
            line = raw_line.strip()
            if not line:
                continue
            heading = _RE_HEADING.match(line)
            if heading:
                flush()
                open_heading(len(heading.group(1)), heading.group(2))
                continue
            bold = _RE_BOLD_HEADING.match(line)
            if bold:
                inner = bold.group(1).strip()
                if _RE_CHAPTER_MARK.match(inner.replace(" ", "")):
                    flush()
                    chapter = _chapter_title(lines, index)
                    if chapter:
                        label, consumed = chapter
                        front_matter = False
                        muted = False
                        push(2, label)
                        skip_until = index + consumed
                    continue
                if open_heading(3, inner, bold=True):
                    flush()
                continue
            if _RE_PAGE_LINE.match(line):
                continue
            if _RE_NUMBERED.match(line):
                flush()
                buffer.append(line)
                continue
            if buffer:
                previous = buffer[-1]
                sentence_done = bool(_RE_SENT_END.search(previous))
                if sentence_done and len(" ".join(buffer)) > 60:
                    following = _next_nonblank(lines, index + 1)
                    if following and _RE_STARTS_UPPER.match(following):
                        flush()
                        buffer.append(line)
                        continue
                buffer[-1] = _join_hyphen(previous, line, vocab)
                continue
            buffer.append(line)
        flush()

    bundle.definitions = sorted(definitions.values(), key=lambda d: (d.section, d.term))
    bundle.truths = list(truths.values())
    # Completa conceptos con los títulos de sección más útiles.
    for section in bundle.sections:
        if 2 <= section.level <= 3 and section.title not in seen_concepts:
            seen_concepts.add(section.title)
            concepts.append(section.title)
    bundle.concepts = concepts
    return bundle


def _definitions_from_sentence(sentence: str, paragraph: Paragraph) -> Iterable[Definition]:
    sentence = sentence.strip()
    if not 40 <= len(sentence) <= 420:
        return
    for pattern in _DEF_PATTERNS:
        match = pattern.match(sentence)
        if not match:
            continue
        term = _clean_term(match.group("term"))
        body = _clean_body(match.group("body"))
        if not term or not body:
            continue
        yield Definition(
            term=term,
            body=body,
            sentence=sentence,
            source=paragraph.source,
            heading_path=paragraph.heading_path,
        )
        return


def _truth_from_sentence(sentence: str, paragraph: Paragraph) -> Truth | None:
    sentence = sentence.strip()
    if not 30 <= len(sentence) <= 260:
        return None
    if not _UNIVERSAL_CUE.search(sentence) or _HEDGE_CUE.search(sentence):
        return None
    if any(token in sentence for token in ("?", "¿", "¡")):
        return None
    if _RE_BOILERPLATE.search(sentence):
        return None
    # Opiniones en primera persona no son verdades incondicionales.
    if re.search(r"\b(yo|mi|mis|me|creo|sospecho|pienso|considero|opino)\b", sentence, re.I):
        return None
    # Afirmaciones sobre un caso concreto no son universales.
    if re.match(
        r"^(en el otro|en el caso|en este caso|en este ejemplo|aqui|alli|entonces|"
        r"por ejemplo|en la situacion|en la situación)",
        _fold(sentence),
    ):
        return None
    # Un demostrativo sin antecedente no se sostiene por sí solo.
    if re.match(r"^(este|esta|esto|estos|estas|ese|esa|eso|aquel|aquella)\b", _fold(sentence)):
        return None
    if "?" in sentence or "¿" in sentence:
        return None
    # Una cita de autor («X objeta que…») no es una verdad del material.
    if re.search(
        r"\b(objeta|senala que|dice que|afirma que|sostiene que|argumenta que|"
        r"critica que|considera que|advierte que|concluye que)\b",
        _fold(sentence),
    ):
        return None
    # Restos de maquetación del PDF dentro de la frase.
    if "*" in sentence or "\u2022" in sentence:
        return None
    if len(sentence.split()) < 7:
        return None
    return Truth(text=sentence, source=paragraph.source, heading_path=paragraph.heading_path)


# ---------------------------------------------------------------------------
# Descubrimiento y carga
# ---------------------------------------------------------------------------

_PREFERRED_FILES = (
    ("libro_principal.md", "libro"),
    ("guia_aprendizaje.md", "guia"),
    ("memory.md", "memoria"),
    ("fuentes_usadas.md", "fuentes"),
)

# Lo que la propia aplicación escribe no es material de estudio: si se releyera,
# las guías generadas se convertirían en «fuente» de las siguientes.
_GENERATED_MARKERS = (
    "guia_",
    "analisis_",
    "_estructura",
    "estructura_ppt",
    "presentacion_",
    "trabajo_",
)


def _is_generated(path: pathlib.Path) -> bool:
    name = path.name.lower()
    return any(marker in name for marker in _GENERATED_MARKERS)


def discover_sources(materia: str) -> list[tuple[pathlib.Path, str]]:
    """Devuelve los archivos de material de una materia, sin duplicados.

    No incluye la carpeta ``materias/<materia>/salidas/``: ahí van los trabajos,
    presentaciones y guías que produce la aplicación, no los libros de origen.
    """
    found: list[tuple[pathlib.Path, str]] = []
    seen: set[pathlib.Path] = set()

    def add(path: pathlib.Path, kind: str) -> None:
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        if resolved in seen or not path.is_file() or _is_generated(path):
            return
        seen.add(resolved)
        found.append((path, kind))

    materia_dir = get_materia_dir(materia)
    for name, kind in _PREFERRED_FILES:
        add(materia_dir / name, kind)
    folder = SALIDAS_DIR / materia
    if folder.is_dir():
        for path in sorted(folder.glob("*.md")):
            add(path, "salida")
    return found


def _fingerprint(materia: str) -> tuple:
    items = []
    for path, kind in discover_sources(materia):
        try:
            stat = path.stat()
        except OSError:
            continue
        items.append((str(path), kind, int(stat.st_mtime_ns), int(stat.st_size)))
    return tuple(items)


@lru_cache(maxsize=6)
def _load_cached(materia: str, fingerprint: tuple) -> MaterialBundle:
    documents: list[tuple[str, str, str]] = []
    for path, kind in discover_sources(materia):
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            documents.append((str(path), kind, ""))
            continue
        documents.append((str(path), kind, raw))
    bundle = build_bundle(materia, documents)
    return bundle


def load_material(materia: str) -> MaterialBundle:
    """Carga (con caché por fecha de modificación) el material de una materia."""
    return _load_cached(materia, _fingerprint(materia))


def invalidate_cache() -> None:
    _load_cached.cache_clear()


def quick_size(materia: str) -> tuple[int, int]:
    """(archivos, caracteres aproximados) sin interpretar el texto.

    Sirve para las pantallas que sólo quieren avisar si hay material, sin pagar
    el coste de analizar un libro entero.
    """
    files = 0
    chars = 0
    for path, _kind in discover_sources(materia):
        try:
            files += 1
            chars += path.stat().st_size
        except OSError:
            continue
    return files, chars


def has_text(materia: str, min_chars: int = 1500) -> bool:
    """¿Hay algo más que la plantilla vacía? Sin analizar el contenido.

    Las plantillas de ``init_materia`` suman ~730 caracteres; la materia de
    ejemplo del paquete ronda los 2.400. El umbral separa ambos casos sin
    tener que interpretar el texto.
    """
    _files, chars = quick_size(materia)
    return chars >= min_chars


# ---------------------------------------------------------------------------
# Utilidades para la interfaz
# ---------------------------------------------------------------------------

def format_sources(bundle: MaterialBundle) -> list[dict[str, str]]:
    rows = []
    for path, kind, chars in bundle.sources:
        rows.append(
            {
                "Archivo": pathlib.Path(path).name,
                "Tipo": KIND_LABELS.get(kind, kind),
                "Caracteres": f"{chars:,}".replace(",", "."),
                "Carpeta": str(pathlib.Path(path).parent),
            }
        )
    return rows


def material_is_placeholder(bundle: MaterialBundle) -> bool:
    """Detecta que lo único que hay es la plantilla creada por init_materia."""
    if not bundle.has_content:
        return True
    marker = "si el facilitador proporciona un libro"
    joined = " ".join(p.text for p in bundle.paragraphs[:6]).lower()
    return marker in joined


if __name__ == "__main__":  # pragma: no cover - utilidad de línea de comandos
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "Teoria_de_la_Personalidad"
    data = load_material(target)
    level, message = data.quality()
    print(f"Materia: {data.materia}")
    print(f"Fuentes: {len(data.sources)} | Caracteres: {data.total_chars:,}")
    print(f"Calidad: {level} — {message}")
    print(f"Párrafos: {len(data.paragraphs)} | Definiciones: {len(data.definitions)}")
    print(f"Verdades: {len(data.truths)} | Secciones: {len(data.sections)}")
    print("\n--- Definiciones ---")
    for definition in data.definitions[:8]:
        print(f"  • {definition.term}: {definition.body[:110]}")
    print("\n--- Afirmaciones universales ---")
    for truth in data.truths[:5]:
        print(f"  • {truth.text[:150]}")
