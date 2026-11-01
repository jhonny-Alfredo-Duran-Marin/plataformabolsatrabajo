"""Pruebas funcionales de caja negra para HU-25 (Búsqueda Semántica de Vacantes).

Cubre los 4 casos de prueba especificados en los criterios de aceptación:
- CP01: Búsqueda en lenguaje natural ("quiero trabajar programando sin atención al público") -> evalúa intención, ordena por score de relevancia (0-100) y expone explicabilidad (razon_coincidencia).
- CP02: Consulta sin coincidencias cercanas -> retorna sugerencias para ampliar la búsqueda.
- CP03: Combinación de búsqueda semántica con filtros estructurados (ciudad, modalidad, etc.).
- CP04: Microservicio de IA apagado -> degradación elegante a búsqueda léxica sin fallar (status 200, ia_disponible=False).
"""

import uuid
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.main import app
from app.models.empresa import Company
from app.models.vacante import JobPosting, JobStatus, WorkModality
from app.security.jwt_provider import create_access_token

client = TestClient(app)


@pytest.fixture
def db_session():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def vacantes_semanticas_fixture(db_session: Session):
    """Crea una empresa y un conjunto de vacantes publicadas para probar afinidad semántica."""
    empresa = Company(
        legal_name=f"Empresa Semantica {uuid.uuid4().hex[:4]} SRL",
        trade_name="Empresa Semántica",
        tax_id=f"NIT-SEM-{uuid.uuid4().hex[:6]}",
        verification_status="verified",
        account_status="active",
    )
    db_session.add(empresa)
    db_session.flush()

    # 1. Vacante de programación pura sin atención a clientes
    v_backend = JobPosting(
        company_id=empresa.id,
        title="Desarrollador Backend Python y Microservicios",
        description="Puesto enfocado en programación, desarrollo de APIs REST, optimización de algoritmos y bases de datos. No requiere interactuar ni atender clientes externos.",
        seniority_level="junior",
        employment_type="permanent",
        work_modality="remote",
        country_code="BO",
        city="Santa Cruz",
        salary_min=Decimal("4500"),
        salary_max=Decimal("6500"),
        status=JobStatus.PUBLISHED.value,
        positions_available=1,
    )
    db_session.add(v_backend)

    # 2. Vacante de atención al público y ventas
    v_ventas = JobPosting(
        company_id=empresa.id,
        title="Ejecutivo de Ventas y Atención al Cliente Presencial",
        description="Atención al cliente en sucursal, llamadas telefónicas diarias a prospectos y venta directa de servicios en mostrador.",
        seniority_level="junior",
        employment_type="permanent",
        work_modality="onsite",
        country_code="BO",
        city="La Paz",
        salary_min=Decimal("3000"),
        salary_max=Decimal("4000"),
        status=JobStatus.PUBLISHED.value,
        positions_available=1,
    )
    db_session.add(v_ventas)

    # 3. Vacante híbrida en Cochabamba
    v_frontend = JobPosting(
        company_id=empresa.id,
        title="Desarrollador Frontend Web",
        description="Desarrollo de interfaces en Angular y TypeScript para sistemas internos de la empresa.",
        seniority_level="junior",
        employment_type="permanent",
        work_modality="hybrid",
        country_code="BO",
        city="Cochabamba",
        salary_min=Decimal("4000"),
        salary_max=Decimal("5500"),
        status=JobStatus.PUBLISHED.value,
        positions_available=1,
    )
    db_session.add(v_frontend)

    db_session.commit()
    return empresa.id, v_backend.id, v_ventas.id, v_frontend.id


def test_cp01_busqueda_lenguaje_natural_score_y_razon(vacantes_semanticas_fixture):
    """CP01: Búsqueda natural ('quiero trabajar programando sin atención al público') prioriza backend técnico sobre ventas."""
    _, backend_id, ventas_id, _ = vacantes_semanticas_fixture

    response = client.get(
        "/api/search/semantic",
        params={"q": "quiero trabajar programando sin atención al público"},
    )
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["ia_disponible"] is True
    assert data["total"] >= 1
    assert "intencion_interpretada" in data
    assert data["intencion_interpretada"].get("area_tecnica") is True
    assert data["intencion_interpretada"].get("excluye_atencion_publico") is True

    items = data["items"]
    # El primer resultado debe ser la vacante backend técnica
    primer_item = items[0]
    assert "backend" in primer_item["title"].lower() or "programación" in primer_item["title"].lower() or "desarrollador" in primer_item["title"].lower()
    assert primer_item["score_relevancia"] >= 50
    assert "razon_coincidencia" in primer_item and len(primer_item["razon_coincidencia"]) > 10

    # Si la vacante de ventas aparece, debe tener un puntaje significativamente menor
    items_ventas = [it for it in items if str(ventas_id) == str(it["id"])]
    if items_ventas:
        assert primer_item["score_relevancia"] > items_ventas[0]["score_relevancia"]


def test_cp02_consulta_sin_coincidencia_ofrece_sugerencias(vacantes_semanticas_fixture):
    """CP02: Si la búsqueda no tiene coincidencias relevantes, ofrece sugerencias para ampliar la consulta."""
    response = client.get(
        "/api/search/semantic",
        params={"q": "astrofísica cuántica aeroespacial en la luna"},
    )
    assert response.status_code == 200
    data = response.json()

    # Si total es 0 o score bajo, debe incluir texto de sugerencia
    if data["total"] == 0 or (data["total"] > 0 and data["items"][0]["score_relevancia"] < 45):
        assert data["sugerencia"] is not None
        assert "sugerimos" in data["sugerencia"].lower() or "intenta" in data["sugerencia"].lower()


def test_cp03_busqueda_semantica_con_filtros_estructurados(vacantes_semanticas_fixture):
    """CP03: Combina la consulta semántica con filtros de ciudad y modalidad."""
    response = client.get(
        "/api/search/semantic",
        params={
            "q": "desarrollo y programación",
            "ciudad": "Cochabamba",
            "modalidad": "hybrid",
        },
    )
    assert response.status_code == 200
    data = response.json()

    for item in data["items"]:
        assert "cochabamba" in item["city"].lower()
        assert item["work_modality"] == "hybrid"


def test_cp04_degradacion_elegante_cuando_ia_apagada(vacantes_semanticas_fixture, monkeypatch):
    """CP04: Cuando el microservicio de IA está apagado, degrada a coincidencia léxica sin romper el endpoint."""
    settings = get_settings()
    monkeypatch.setattr(settings, "ia_recomendaciones_activas", False)

    response = client.get(
        "/api/search/semantic",
        params={"q": "Python backend"},
    )
    # Debe responder con 200 OK y no 500/503
    assert response.status_code == 200
    data = response.json()

    assert data["ia_disponible"] is False
    assert data["sugerencia"] is not None
    assert "mantenimiento" in data["sugerencia"].lower() or "compatibilidad" in data["sugerencia"].lower()

    # Alias /api/ia/busqueda-semantica también debe responder con degradación elegante
    r_alias = client.get("/api/ia/busqueda-semantica", params={"q": "Python"})
    assert r_alias.status_code == 200
    assert r_alias.json()["ia_disponible"] is False

