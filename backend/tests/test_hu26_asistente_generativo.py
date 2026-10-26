"""Pruebas funcionales de caja negra para HU-26 (Asistente Generativo de Resumen Profesional).

Cubre los 4 casos de prueba especificados:
- CP01: Perfil con experiencia y habilidades -> solicita generación -> borrador editable basado en datos del perfil.
- CP02: Borrador generado -> editar texto antes de guardar -> el sistema conserva los cambios manuales.
- CP03: Borrador no satisfactorio -> solicitar generar nuevamente -> entrega nueva versión con redacción alternativa.
- CP04: Microservicio de IA no disponible -> devuelve 503 con mensaje claro permitiendo redacción manual.
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.security.jwt_provider import create_access_token


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def candidato_token():
    # Egresado Antonio Prueba de la UAGRM con perfil, experiencia y habilidades cargadas
    user_id = "90000000-0000-0000-0000-000000000003"
    token = create_access_token(user_id, "candidate", extra_claims={"roles": ["candidate"]})
    return token, user_id


def test_cp01_generar_resumen_basado_en_perfil(client, candidato_token):
    """CP01: El sistema devuelve un borrador editable basado en los datos del perfil."""
    token, _ = candidato_token

    response = client.post(
        "/api/ia/resumen-profesional/generar",
        headers={"Authorization": f"Bearer {token}"},
        json={"variante": 1, "enfoque": "general"},
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["generado_por_ia"] is True
    assert "borrador" in data and len(data["borrador"]) > 40
    assert "advertencia" in data
    assert "revisión" in data["advertencia"].lower()
    assert data["variante"] == 1
    assert "datos_utilizados" in data


def test_cp02_editar_borrador_antes_de_guardar(client, candidato_token):
    """CP02: El egresado edita el texto del borrador generado y el sistema conserva sus cambios manuales."""
    token, _ = candidato_token

    # 1. Generar borrador
    r_gen = client.post(
        "/api/ia/resumen-profesional/generar",
        headers={"Authorization": f"Bearer {token}"},
        json={"variante": 1},
    )
    assert r_gen.status_code == 200
    borrador = r_gen.json()["borrador"]

    # 2. Modificación manual explícita del egresado
    texto_editado_manualmente = f"{borrador} [Ajuste manual del egresado para enfatizar liderazgo]."

    # 3. Guardar en el perfil vía PATCH /api/perfiles/me
    r_save = client.patch(
        "/api/perfiles/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"resumen_profesional": texto_editado_manualmente},
    )
    assert r_save.status_code == 200

    # 4. Verificar que se conservaron los cambios manuales
    r_get = client.get("/api/perfiles/me", headers={"Authorization": f"Bearer {token}"})
    assert r_get.status_code == 200
    assert r_get.json()["resumen_profesional"] == texto_editado_manualmente


def test_cp03_generar_nuevamente_entrega_nueva_version(client, candidato_token):
    """CP03: Si el egresado no queda conforme, solicita generar nuevamente y recibe una versión alternativa."""
    token, _ = candidato_token

    # Versión 1
    r_v1 = client.post(
        "/api/ia/resumen-profesional/generar",
        headers={"Authorization": f"Bearer {token}"},
        json={"variante": 1},
    )
    assert r_v1.status_code == 200
    borrador_v1 = r_v1.json()["borrador"]

    # Versión 2 (Regenerar)
    r_v2 = client.post(
        "/api/ia/resumen-profesional/generar",
        headers={"Authorization": f"Bearer {token}"},
        json={"variante": 2},
    )
    assert r_v2.status_code == 200
    borrador_v2 = r_v2.json()["borrador"]

    assert borrador_v1 != borrador_v2
    assert r_v2.json()["variante"] == 2


def test_cp04_servicio_ia_no_disponible(client, candidato_token, monkeypatch):
    """CP04: Cuando el microservicio de IA no está disponible, el sistema informa el error amigablemente."""
    token, _ = candidato_token

    # Simular microservicio de IA apagado
    settings = get_settings()
    monkeypatch.setattr(settings, "ia_recomendaciones_activas", False)

    response = client.post(
        "/api/ia/resumen-profesional/generar",
        headers={"Authorization": f"Bearer {token}"},
        json={"variante": 1},
    )

    # 503 Service Unavailable
    assert response.status_code == 503
    assert "no está disponible" in response.json()["detail"].lower()
    assert "manualmente" in response.json()["detail"].lower()
