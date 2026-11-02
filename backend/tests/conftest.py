import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def bitacora_en_claro(monkeypatch):
    """Los tests leen la bitácora en claro aunque el .env local tenga BITACORA_CLAVE_PUBLICA.

    Los que prueban la bitácora cifrada vuelven a poner la clave con su propio fixture.
    """
    monkeypatch.setattr(get_settings(), "bitacora_clave_publica", None)


@pytest.fixture(autouse=True)
def sin_gemini(monkeypatch):
    """Ningún test llama a Gemini aunque el .env local tenga las claves: sin clave, el chatbot
    y los borradores responden con sus reglas. Los que prueban Gemini ponen una clave falsa y
    reemplazan ia_generativa.generar_json."""
    monkeypatch.setattr(get_settings(), "gemini_api_key_asistente", None)
    monkeypatch.setattr(get_settings(), "gemini_api_key_reportes", None)
