import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def bitacora_en_claro(monkeypatch):
    """Los tests leen la bitácora en claro aunque el .env local tenga BITACORA_CLAVE_PUBLICA.

    Los que prueban la bitácora cifrada vuelven a poner la clave con su propio fixture.
    """
    monkeypatch.setattr(get_settings(), "bitacora_clave_publica", None)
