"""IA generativa con Google Gemini: chatbot, borradores (HU-26/27/28) y reportes pedidos en
lenguaje natural.

Cada uso tiene su clave (GEMINI_API_KEY_ASISTENTE, GEMINI_API_KEY_REPORTES). Sin clave, o si
Gemini no responde a tiempo, se lanza IAGenerativaNoDisponible y quien llama sigue con su
alternativa. A Gemini se le manda solo lo que la respuesta necesita: nunca contraseñas,
correos, teléfonos ni documentos.
"""

import json
import logging
import re
from typing import Any, Literal

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_URL = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
_TIEMPO_MAXIMO = 20
# "Modelo sobrecargado" es frecuente en el plan gratuito y suele pasar al reintentar.
_REINTENTABLES = {500, 502, 503, 504}
_SIN_CUOTA = 429

Uso = Literal["asistente", "reportes"]


class IAGenerativaNoDisponible(Exception):
    """Gemini no está configurado o no respondió bien; quien llama usa su alternativa."""


def _clave(uso: Uso) -> str | None:
    s = get_settings()
    return s.gemini_api_key_asistente if uso == "asistente" else s.gemini_api_key_reportes


def disponible(uso: Uso) -> bool:
    return bool(_clave(uso))


def _modelos() -> list[str]:
    return list(dict.fromkeys(m for m in get_settings().gemini_modelos if m))


def _pedir(modelo: str, clave: str, cuerpo: dict[str, Any], uso: Uso) -> httpx.Response | None:
    """Una llamada, con un reintento si el modelo está sobrecargado; None si no respondió."""
    for intento in (1, 2):
        try:
            respuesta = httpx.post(
                _URL.format(modelo=modelo), headers={"x-goog-api-key": clave}, json=cuerpo, timeout=_TIEMPO_MAXIMO
            )
        except httpx.HTTPError as exc:
            logger.warning("Gemini %s (%s) no respondió: %s", modelo, uso, type(exc).__name__)
            return None
        if respuesta.status_code not in _REINTENTABLES or intento == 2:
            return respuesta
    return None


def generar_json(
    uso: Uso,
    instrucciones: str,
    mensajes: list[tuple[str, str]],
    esquema: dict[str, Any],
    temperatura: float = 0.4,
) -> tuple[dict[str, Any], str]:
    """Pide a Gemini una respuesta JSON con la forma de `esquema`; devuelve (datos, modelo que respondió).

    `mensajes` es la conversación en orden: ("user" | "model", texto).
    """
    clave = _clave(uso)
    if not clave:
        raise IAGenerativaNoDisponible("Falta la clave de Gemini.")
    cuerpo = {
        "systemInstruction": {"parts": [{"text": instrucciones}]},
        "contents": [{"role": rol, "parts": [{"text": texto}]} for rol, texto in mensajes],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseJsonSchema": esquema,
            "temperature": temperatura,
            "thinkingConfig": {"thinkingLevel": "low"},
        },
    }
    for modelo in _modelos():
        respuesta = _pedir(modelo, clave, cuerpo, uso)
        if respuesta is not None and respuesta.status_code == 200:
            return _leer(respuesta, uso), modelo
        if respuesta is not None:
            # El cuerpo del error es de Google (cuota, clave, modelo); no trae datos del usuario.
            logger.warning("Gemini %s (%s) respondió %s: %s", modelo, uso, respuesta.status_code, respuesta.text[:300])
            # Un error de clave o de pedido no se arregla cambiando de modelo; sin cuota o caído, sí.
            if respuesta.status_code != _SIN_CUOTA and respuesta.status_code not in _REINTENTABLES:
                break
    raise IAGenerativaNoDisponible("Gemini no respondió.")


def _leer(respuesta: httpx.Response, uso: Uso) -> dict[str, Any]:
    try:
        partes = respuesta.json()["candidates"][0]["content"]["parts"]
        datos = json.loads("".join(p.get("text", "") for p in partes if not p.get("thought")))
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        logger.warning("Gemini (%s) devolvió una respuesta sin el formato pedido.", uso)
        raise IAGenerativaNoDisponible("Respuesta de Gemini inesperada.") from exc
    if not isinstance(datos, dict):
        raise IAGenerativaNoDisponible("Respuesta de Gemini inesperada.")
    return datos


def texto_para_chat(texto: str) -> str:
    """Deja solo el formato que muestran la web y la app: **negrita**, `código`, viñetas «•»."""
    lineas = []
    for linea in texto.strip().splitlines():
        linea = re.sub(r"^\s*#{1,6}\s*", "", linea)
        linea = re.sub(r"^(\s*)[-*]\s+", r"\1• ", linea)
        # La web no muestra la cursiva con un asterisco: queda como texto común.
        linea = re.sub(r"(?<!\*)\*(?!\*)([^*\n]+?)(?<!\*)\*(?!\*)", r"\1", linea)
        lineas.append(linea.rstrip())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lineas)).strip()
