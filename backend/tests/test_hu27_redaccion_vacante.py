"""Pruebas funcionales de caja negra para HU-27 (Redacción Asistida de Vacante con IA).

Cubre los 4 casos de prueba especificados en los criterios de aceptación:
- CP01: Empresa envía indicación breve -> recibe borrador estructurado en 3 secciones (descripción, requisitos, beneficios) con título, modalidad y seniority inferidos.
- CP02: Empresa solicita generar nuevamente con variante diferente -> recibe redacción alternativa y diferenciada.
- CP03: Creación de vacante con IA -> se registra en audit_log con marca "Asistida por IA", indicación original y fecha.
- CP04: Microservicio de IA no disponible -> devuelve 503 con mensaje claro permitiendo redacción manual.
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.main import app
from app.models.empresa import Company, CompanyMember
from app.models.seguridad import AuditLog
from app.models.usuario import AppUser, Role, UserRole
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
def empresa_fixture(db_session: Session):
    """Crea una empresa verificada con un usuario miembro para pruebas de redacción de vacantes."""
    # Asegurar roles
    for r_name in ("empresa", "candidate", "platform_admin"):
        if not db_session.query(Role).filter_by(name=r_name).first():
            db_session.add(Role(name=r_name))
    db_session.commit()

    user = AppUser(
        email=f"reclutador_{uuid.uuid4().hex[:6]}@techcompany.bo",
        password_hash="fakehash",
        account_status="active",
    )
    db_session.add(user)
    db_session.flush()

    role_empresa = db_session.query(Role).filter_by(name="empresa").first()
    db_session.add(UserRole(user_id=user.id, role_id=role_empresa.id))

    company = Company(
        legal_name=f"Tech Corp {uuid.uuid4().hex[:4]} SRL",
        trade_name="Tech Corp",
        tax_id=f"NIT-{uuid.uuid4().hex[:8]}",
        verification_status="verified",
        account_status="active",
    )
    db_session.add(company)
    db_session.flush()

    member = CompanyMember(
        company_id=company.id,
        user_id=user.id,
        member_type="owner",
        is_active=True,
    )
    db_session.add(member)
    db_session.commit()

    token = create_access_token(str(user.id), "empresa", extra_claims={"roles": ["empresa"]})
    return token, user.id, company.id


def test_cp01_generar_borrador_vacante_con_ia(empresa_fixture):
    """CP01: Empresa envía indicación breve y recibe un borrador con 3 secciones editables."""
    token, user_id, _ = empresa_fixture

    payload = {
        "indicacion": "Desarrollador backend junior, remoto, python y bases de datos sql",
        "variante": 1,
    }

    # Probar endpoint /api/ia/job-description
    response = client.post(
        "/api/ia/job-description",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert response.status_code == 200, response.text
    data = response.json()

    # Validar las 3 secciones requeridas
    assert "descripcion" in data and len(data["descripcion"]) > 40
    assert "requisitos" in data and isinstance(data["requisitos"], list) and len(data["requisitos"]) >= 3
    assert "beneficios" in data and isinstance(data["beneficios"], list) and len(data["beneficios"]) >= 3

    # Validar metadatos inferidos
    assert "titulo" in data and "backend" in data["titulo"].lower()
    assert data["modalidad"] == "remote"
    assert data["seniority"] == "junior"
    assert data["generado_por_ia"] is True
    assert data["marca_auditoria"] == "Asistida por IA"

    # Validar alias /api/ai/job-description
    response_ai = client.post(
        "/api/ai/job-description",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert response_ai.status_code == 200


def test_cp02_generar_variantes_alternativas(empresa_fixture):
    """CP02: Si la empresa solicita regenerar, recibe variantes de redacción alternativas."""
    token, _, _ = empresa_fixture

    payload_v1 = {
        "indicacion": "Analista de datos junior, sql y python",
        "variante": 1,
    }
    r1 = client.post("/api/ia/job-description", headers={"Authorization": f"Bearer {token}"}, json=payload_v1)
    assert r1.status_code == 200
    data_v1 = r1.json()

    payload_v2 = {
        "indicacion": "Analista de datos junior, sql y python",
        "variante": 2,
    }
    r2 = client.post("/api/ia/job-description", headers={"Authorization": f"Bearer {token}"}, json=payload_v2)
    assert r2.status_code == 200
    data_v2 = r2.json()

    # Las descripciones deben ser diferentes por el cambio de tono y estilo
    assert data_v1["descripcion"] != data_v2["descripcion"]
    assert data_v1["requisitos"] != data_v2["requisitos"]


def test_cp03_creacion_vacante_asistida_ia_auditoria(empresa_fixture, db_session: Session):
    """CP03: Crear la vacante asistida por IA registra en audit_log la marca y los metadatos."""
    token, user_id, company_id = empresa_fixture

    # 1. Crear vacante indicando asistida_por_ia
    vacante_payload = {
        "title": "Desarrollador Python Junior IA",
        "description": "Descripción redactada con asistencia de IA para desarrollo backend en Python.",
        "responsibilities_json": ["Desarrollo de APIs REST", "Pruebas unitarias"],
        "requirements_json": ["Python intermedio", "PostgreSQL"],
        "benefits_json": ["Trabajo remoto", "Capacitación continua"],
        "seniority_level": "junior",
        "employment_type": "permanent",
        "work_modality": "remote",
        "country_code": "BO",
        "city": "Santa Cruz",
        "salary_min": 4000,
        "salary_max": 6000,
        "positions_available": 1,
        "status": "draft",
        "asistida_por_ia": True,
        "indicacion_ia": "Desarrollador Python junior remoto para startup",
    }

    r_crear = client.post(
        "/api/vacantes",
        headers={"Authorization": f"Bearer {token}"},
        json=vacante_payload,
    )
    assert r_crear.status_code == 201, r_crear.text
    vacante_creada = r_crear.json()
    assert vacante_creada["asistida_por_ia"] is True

    # 2. Verificar en la bitácora de auditoría (audit_log)
    vacante_id = uuid.UUID(vacante_creada["id"])
    log = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.entity_id == vacante_id,
            AuditLog.action == "create_job_posting",
        )
        .first()
    )
    assert log is not None
    assert log.details_json is not None
    assert log.details_json.get("asistida_por_ia") is True
    assert log.details_json.get("marca") == "Asistida por IA"
    assert log.details_json.get("indicacion_ia") == "Desarrollador Python junior remoto para startup"


def test_cp04_servicio_ia_no_disponible(empresa_fixture, monkeypatch):
    """CP04: Cuando el microservicio de IA está apagado, retorna 503 con mensaje explicativo."""
    token, _, _ = empresa_fixture

    settings = get_settings()
    monkeypatch.setattr(settings, "ia_recomendaciones_activas", False)

    response = client.post(
        "/api/ia/job-description",
        headers={"Authorization": f"Bearer {token}"},
        json={"indicacion": "Desarrollador frontend react junior"},
    )
    assert response.status_code == 503
    assert "no está disponible" in response.json()["detail"].lower()
    assert "manualmente" in response.json()["detail"].lower()

