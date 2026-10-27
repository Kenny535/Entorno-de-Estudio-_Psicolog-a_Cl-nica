#!/usr/bin/env python3
"""
Cliente opcional para modelos de lenguaje.

La aplicación funciona sin IA (todo se genera desde el texto del material).
Si el usuario configura un endpoint compatible con la API de OpenAI —o un
Ollama/LM Studio local— el sistema lo usa para redactar la lección con voz de
profesor, manteniendo las preguntas ancladas al texto.

La clave se guarda **sólo en local** (`recursos/ia_config.json`) y nunca se
escribe en los registros ni se muestra completa en la interfaz.
"""

from __future__ import annotations

import json
import os
import re
import socket
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests

from config import BASE_DIR

CONFIG_PATH = BASE_DIR / "recursos" / "ia_config.json"

PRESETS: dict[str, dict[str, str]] = {
    "deepseek": {
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
    },
    "openai": {
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
    },
    "ollama": {
        "label": "Ollama (local)",
        "base_url": "http://localhost:11434/v1",
        "model": "llama3.1",
    },
    "lmstudio": {
        "label": "LM Studio (local)",
        "base_url": "http://localhost:1234/v1",
        "model": "local-model",
    },
    "custom": {
        "label": "Otro (compatible OpenAI)",
        "base_url": "",
        "model": "",
    },
}


class AIError(RuntimeError):
    """Error de configuración, red o respuesta del modelo."""


@dataclass
class AIConfig:
    enabled: bool = False
    preset: str = "deepseek"
    base_url: str = PRESETS["deepseek"]["base_url"]
    model: str = PRESETS["deepseek"]["model"]
    api_key: str = ""
    temperature: float = 0.4
    timeout: int = 90
    max_tokens: int = 900

    # -- persistencia -----------------------------------------------------
    @classmethod
    def load(cls) -> "AIConfig":
        config = cls()
        if CONFIG_PATH.is_file():
            try:
                raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                raw = {}
            for key in ("enabled", "preset", "base_url", "model", "api_key",
                        "temperature", "timeout", "max_tokens"):
                if key in raw:
                    setattr(config, key, raw[key])
        # Variables de entorno: permiten usar la app sin guardar la clave.
        config.api_key = os.environ.get("ESTUDIO_IA_API_KEY", config.api_key)
        config.base_url = os.environ.get("ESTUDIO_IA_BASE_URL", config.base_url)
        config.model = os.environ.get("ESTUDIO_IA_MODEL", config.model)
        return config

    def save(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        try:
            os.chmod(CONFIG_PATH, 0o600)
        except OSError:
            pass

    # -- propiedades ------------------------------------------------------
    @property
    def is_local(self) -> bool:
        host = (urlparse(self.base_url or "").hostname or "").lower()
        return host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}

    @property
    def resolved_key(self) -> str:
        return self.api_key.strip()

    def describe(self) -> str:
        if not self.enabled:
            return "Sin IA (modo local)"
        label = PRESETS.get(self.preset, {}).get("label", self.preset)
        return f"{label} · {self.model}"

    def masked_key(self) -> str:
        key = self.resolved_key
        if not key:
            return "(sin clave)"
        if len(key) <= 8:
            return "•" * len(key)
        return f"{key[:4]}…{key[-4:]}"


def _clean_base_url(base_url: str) -> str:
    base = (base_url or "").strip().rstrip("/")
    if not base:
        raise AIError("Falta la dirección del servicio de IA (base URL).")
    if not re.match(r"^https?://", base):
        raise AIError("La dirección debe empezar por http:// o https://")
    return base


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except ValueError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except ValueError as exc:
            raise AIError(f"El modelo no devolvió JSON válido: {exc}") from exc
    raise AIError("El modelo no devolvió JSON.")


@dataclass
class AIClient:
    config: AIConfig

    # -- básicos ----------------------------------------------------------
    @property
    def available(self) -> bool:
        if not self.config.enabled:
            return False
        if self.config.is_local:
            return bool(self.config.base_url)
        return bool(self.config.resolved_key and self.config.base_url)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        key = self.config.resolved_key
        if key:
            headers["Authorization"] = f"Bearer {key}"
        return headers

    def _endpoint(self, suffix: str) -> str:
        return f"{_clean_base_url(self.config.base_url)}{suffix}"

    def status(self) -> tuple[bool, str]:
        """Comprueba la conexión sin gastar tokens (GET /models)."""
        if not self.config.enabled:
            return False, "La IA está desactivada."
        if not self.config.base_url:
            return False, "Falta la dirección del servicio."
        if not self.config.is_local and not self.config.resolved_key:
            return False, "Falta la clave de API."
        try:
            response = requests.get(
                self._endpoint("/models"),
                headers=self._headers(),
                timeout=8,
            )
        except requests.RequestException as exc:
            return False, f"No se pudo conectar: {_short_error(exc)}"
        if response.status_code == 401:
            return False, "La clave fue rechazada (401)."
        if response.status_code >= 400:
            return False, f"El servicio respondió {response.status_code}."
        return True, f"Conectado a {self.config.describe()}."

    # -- generación -------------------------------------------------------
    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> str:
        if not self.available:
            raise AIError("La IA no está configurada o está desactivada.")
        payload: dict = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature if temperature is None else temperature,
            "max_tokens": self.config.max_tokens if max_tokens is None else max_tokens,
            "stream": False,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        try:
            response = requests.post(
                self._endpoint("/chat/completions"),
                headers=self._headers(),
                json=payload,
                timeout=self.config.timeout,
            )
        except requests.Timeout as exc:
            raise AIError("El modelo tardó demasiado en responder.") from exc
        except requests.RequestException as exc:
            raise AIError(f"No se pudo conectar: {_short_error(exc)}") from exc

        if response.status_code == 401:
            raise AIError("La clave de API fue rechazada (401).")
        if response.status_code == 404:
            raise AIError(
                "El servicio no encontró el modelo o la ruta. Revisa la dirección "
                "y el nombre del modelo."
            )
        if response.status_code >= 400:
            detail = ""
            try:
                body = response.json()
                detail = body.get("error", {}).get("message", "") if isinstance(body, dict) else ""
            except ValueError:
                detail = response.text[:200]
            raise AIError(f"El servicio respondió {response.status_code}. {detail}".strip())

        try:
            data = response.json()
            return data["choices"][0]["message"]["content"] or ""
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise AIError("Respuesta inesperada del servicio de IA.") from exc

    def chat_json(self, messages: list[dict[str, str]], **kwargs) -> dict:
        text = self.chat(messages, json_mode=True, **kwargs)
        return _extract_json(text)


def _short_error(exc: Exception) -> str:
    text = str(exc)
    text = re.sub(r"https?://\S+", "[dirección]", text)
    return text[:160]


def detect_local_models(timeout: float = 0.6) -> list[AIConfig]:
    """Busca servicios locales habituales (Ollama, LM Studio)."""
    found: list[AIConfig] = []
    candidates = [
        ("ollama", "http://localhost:11434", {"llama3.1"}),
        ("lmstudio", "http://localhost:1234", {"local-model"}),
    ]
    for preset, base, models in candidates:
        parsed = urlparse(base)
        try:
            with socket.create_connection((parsed.hostname, parsed.port), timeout=timeout):
                pass
        except OSError:
            continue
        model = PRESETS[preset]["model"]
        try:
            response = requests.get(f"{base}/v1/models", timeout=2)
            if response.ok:
                data = response.json()
                names = [item.get("id", "") for item in data.get("data", [])]
                names = [name for name in names if name]
                if names:
                    model = names[0]
        except (requests.RequestException, ValueError, AttributeError):
            pass
        found.append(
            AIConfig(
                enabled=True,
                preset=preset,
                base_url=f"{base}/v1",
                model=model,
            )
        )
    return found


# ---------------------------------------------------------------------------
# Prompts del sistema
# ---------------------------------------------------------------------------

TEACHER_SYSTEM = """Eres un profesor de psicología clínica que enseña siguiendo dos
principios comprobados:

1. Verdades incondicionales primero: empieza por los hechos que se aceptan tal
   cual, sin matices, y construye desde ahí.
2. Cada paso se motiva como algo que el estudiante podría haber descubierto:
   nunca aparece de la nada. Nada de «porque sí».

Escribes en español neutro, claro y directo, sin relleno. No inventas datos: te
apoyas exclusivamente en los extractos del material que recibes. Si el material
no alcanza para afirmar algo, lo dices.

Formato: Markdown breve con párrafos cortos. Usa LaTeX ($...$) si hay notación.
Nunca incluyes una lista de opciones ni preguntas de examen en la explicación.
"""

PLANNER_SYSTEM = """Eres un diseñador de planes de estudio. Recibes la meta del
estudiante y extractos reales de su material. Devolves un plan en JSON con la
forma exacta:

{
  "narrative": "2-4 frases explicando el enfoque y por qué ese orden",
  "roots": [{"label": "...", "statement": "...", "quote": "..."}],
  "nodes": [{"label": "...", "statement": "...", "quote": "...", "depends_on": "etiqueta de otro nodo o ''"}],
  "goal": "la meta reformulada en una frase"
}

Reglas:
- Las raíces son hechos que el material sostiene sin excepciones.
- Cada nodo debe depender de algo anterior (raíz u otro nodo).
- Usa las palabras del material; no inventes conceptos que no aparezcan.
- Entre 3 y 6 nodos. Etiquetas de 2 a 6 palabras.
"""


def build_teacher_messages(
    materia: str,
    goal: str,
    node_label: str,
    statement: str,
    quote: str,
    context: str,
    previous: list[str],
) -> list[dict[str, str]]:
    previous_text = "\n".join(f"- {item}" for item in previous) or "(nada todavía)"
    user = f"""Materia: {materia}
Meta del estudiante: {goal}

Ideas ya fijadas:
{previous_text}

Nodo actual: {node_label}
Afirmación del material: {statement}
Extracto textual: {quote}
Fuente: {context}

Escribe la explicación de este nodo con esta estructura exacta, en Markdown:

**Por qué ahora.** 2-3 frases: qué problema resuelve este nodo y por qué viene
después de lo anterior (motivación, no anuncio).

**La idea.** 3-5 frases que establecen el nodo apoyándose en el extracto, como
si el estudiante lo estuviera descubriendo.

**Cómo se conecta.** 1-3 frases que hacen explícito el enlace con la idea
anterior (o con la base, si es una raíz).

No repitas literalmente el extracto; úsalo. No añadas preguntas.
"""
    return [
        {"role": "system", "content": TEACHER_SYSTEM},
        {"role": "user", "content": user},
    ]


def build_planner_messages(
    materia: str, goal: str, excerpts: str, truths: list[str]
) -> list[dict[str, str]]:
    truths_text = "\n".join(f"- {truth}" for truth in truths) or "(ninguna detectada)"
    user = f"""Materia: {materia}
Meta del estudiante: {goal}

Verdades incondicionales detectadas en el material:
{truths_text}

Extractos del material:
{excerpts}

Devuelve el plan en JSON.
"""
    return [
        {"role": "system", "content": PLANNER_SYSTEM},
        {"role": "user", "content": user},
    ]
