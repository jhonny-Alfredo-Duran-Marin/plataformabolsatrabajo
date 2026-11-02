"""Pruebas funcionales de caja negra para HU-32 (Exportación de Reportes del Tablero de Indicadores) y HU-31.

Cubre los 4 casos de prueba especificados en los criterios de aceptación:
- CP01: Exportación a PDF con formato institucional legible, fecha/hora Bolivia y filtros aplicados.
- CP02: Exportación a Excel (.xlsx) estructurado en celdas con estilos corporativos.
- CP03: Registro de cada operación de exportación en la bitácora de auditoría (audit_log).
- CP04: Manejo adecuado de muestra insuficiente (< 5 casos) sin fallar ni arrojar errores.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.main import app
from app.models.candidato import CandidateEducation, CandidateProfile
from app.models.catalogo import FieldOfStudy
from app.models.colocacion import Placement
from app.models.institucion import Institution
from app.models.seguridad import AuditLog
from app.models.usuario import AppUser, Role, UserRole
from app.security import cifrado_bitacora as cifrado
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
def admin_universidad_fixture(db_session: Session):
    """Crea una institución universitaria y un usuario administrador para pruebas de indicadores."""
    for r_name in ("platform_admin", "moderator", "candidate"):
        if not db_session.query(Role).filter_by(name=r_name).first():
            db_session.add(Role(name=r_name))
    db_session.commit()

    inst = Institution(
        name=f"Universidad Tecnológica {uuid.uuid4().hex[:4]}",
        is_tenant=True,
    )
    db_session.add(inst)
    db_session.flush()

    user = AppUser(
        email=f"admin_uni_{uuid.uuid4().hex[:6]}@universidad.edu.bo",
        password_hash="fakehash",
        account_status="active",
        institution_id=inst.id,
    )
    db_session.add(user)
    db_session.flush()

    role_admin = db_session.query(Role).filter_by(name="platform_admin").first()
    db_session.add(UserRole(user_id=user.id, role_id=role_admin.id))

    carrera = FieldOfStudy(name=f"Ingeniería de Software {uuid.uuid4().hex[:4]}", category="Tecnología")
    db_session.add(carrera)
    db_session.flush()

    # Crear 6 egresados y colocaciones para tener muestra suficiente (>= 5 casos)
    for i in range(6):
        cand_user = AppUser(
            email=f"egresado_{uuid.uuid4().hex[:6]}@test.edu.bo",
            password_hash="fake",
            account_status="active",
            institution_id=inst.id,
        )
        db_session.add(cand_user)
        db_session.flush()

        perfil = CandidateProfile(
            user_id=cand_user.id,
            first_name=f"Egresado{i}",
            last_name="Prueba",
            institution_id=inst.id,
            verification_status="verified",
        )
        db_session.add(perfil)
        db_session.flush()

        colocacion = Placement(
            candidate_id=perfil.id,
            institution_id=inst.id,
            company_name="Empresa Contratante SRL",
            position_title="Desarrollador Junior",
            start_date=date(2026, 1, 15),
            salary=Decimal("5000"),
            currency="BOB",
            status="confirmed",
            source="manual",
        )
        db_session.add(colocacion)

    db_session.commit()

    token = create_access_token(
        str(user.id),
        "platform_admin",
        extra_claims={"roles": ["platform_admin"], "institution_id": str(inst.id)},
    )
    return token, user.id, inst.id, carrera.id


def test_cp01_exportar_indicadores_pdf(admin_universidad_fixture):
    """CP01: Exportación a PDF con formato institucional y fecha de emisión."""
    token, _, inst_id, _ = admin_universidad_fixture

    # Vía GET /api/indicators/export?format=pdf
    response = client.get(
        "/api/indicators/export",
        headers={"Authorization": f"Bearer {token}"},
        params={"format": "pdf"},
    )
    assert response.status_code == 200, response.text
    assert response.headers["Content-Type"] == "application/pdf"
    assert "attachment" in response.headers["Content-Disposition"]
    assert response.headers["Content-Disposition"].endswith('.pdf"')

    # El contenido binario debe ser un PDF válido (%PDF-)
    assert response.content.startswith(b"%PDF-")

    # Vía POST /api/indicators/export
    r_post = client.post(
        "/api/indicators/export",
        headers={"Authorization": f"Bearer {token}"},
        json={"formato": "pdf"},
    )
    assert r_post.status_code == 200
    assert r_post.content.startswith(b"%PDF-")


def test_cp02_exportar_indicadores_excel(admin_universidad_fixture):
    """CP02: Exportación a Excel (.xlsx) con celdas estructuradas."""
    token, _, _, _ = admin_universidad_fixture

    response = client.get(
        "/api/indicators/export",
        headers={"Authorization": f"Bearer {token}"},
        params={"format": "xlsx"},
    )
    assert response.status_code == 200, response.text
    assert "openxmlformats-officedocument.spreadsheetml.sheet" in response.headers["Content-Type"]
    assert ".xlsx" in response.headers["Content-Disposition"]

    # Los archivos .xlsx son archivos ZIP (comienzan con la firma de archivo 'PK')
    assert response.content.startswith(b"PK")


def test_cp03_registro_auditoria_exportacion(admin_universidad_fixture, db_session: Session):
    """CP03: La exportación de indicadores se registra de manera trazable en audit_log."""
    token, user_id, _, _ = admin_universidad_fixture

    r = client.get(
        "/api/indicators/export",
        headers={"Authorization": f"Bearer {token}"},
        params={"format": "pdf", "periodo": "2026"},
    )
    assert r.status_code == 200

    log = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.user_id == user_id,
            AuditLog.action == "exportar_reporte_indicadores",
        )
        .order_by(AuditLog.created_at.desc())
        .first()
    )
    assert log is not None
    assert log.entity_type == "reportes"
    assert log.result == "success"
    detalle = log.details_json["detalle"]
    assert "formato=pdf" in detalle
    assert "periodo=2026" in detalle


def test_la_exportacion_queda_cifrada_en_la_bitacora(admin_universidad_fixture, db_session: Session, monkeypatch):
    """Con la clave de desarrollador configurada (como en producción) la exportación no queda en texto plano."""
    token, user_id, _, _ = admin_universidad_fixture
    clave = cifrado.generar_clave_desarrollador()
    publica = cifrado.clave_publica_de(clave)
    monkeypatch.setattr(get_settings(), "bitacora_clave_publica", publica)

    r = client.get("/api/indicators/export", headers={"Authorization": f"Bearer {token}"}, params={"format": "xlsx"})
    assert r.status_code == 200

    assert db_session.query(AuditLog).filter(AuditLog.user_id == user_id).count() == 0
    lector = cifrado.Lector(clave, publica)
    desde = datetime.now(timezone.utc) - timedelta(days=1)
    entradas = []
    for log in db_session.query(AuditLog).filter(AuditLog.payload_cifrado.is_not(None), AuditLog.created_at >= desde):
        try:
            entradas.append(lector.descifrar(log.payload_cifrado))
        except Exception:
            continue  # cifrada con otra clave
    assert any(e["a"] == "exportar_reporte_indicadores" and e["u"] == str(user_id) for e in entradas)


def test_sin_datos_no_se_inventan_indicadores(admin_universidad_fixture):
    """Colocaciones manuales sin encuestas ni fecha de egreso: tiempo y pertinencia quedan vacíos (no 4.5 meses ni 80 %)."""
    token, _, _, _ = admin_universidad_fixture

    r = client.get("/api/indicators", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["tiempo_promedio_primer_empleo_meses"] is None
    assert data["pertinencia_carrera_porcentaje"] is None
    # Las colocaciones manuales no vienen de una vacante: su modalidad no se conoce.
    assert data["colocaciones_por_modalidad"]["onsite"] == 0
    assert data["colocaciones_por_modalidad"]["sin_dato"] == 6


def test_el_tiempo_al_primer_empleo_se_mide_desde_el_egreso(admin_universidad_fixture, db_session: Session):
    """Sin respuestas de encuesta, el tiempo sale de la fecha de egreso y el inicio del empleo (15/07/2025 -> 15/01/2026)."""
    token, _, inst_id, _ = admin_universidad_fixture
    for perfil in db_session.query(CandidateProfile).filter(CandidateProfile.institution_id == inst_id):
        db_session.add(
            CandidateEducation(
                candidate_id=perfil.id,
                program_name="Ingeniería de Software",
                academic_status="graduated",
                graduation_date=date(2025, 7, 15),
            )
        )
    db_session.commit()

    r = client.get("/api/indicators", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    assert r.json()["tiempo_promedio_primer_empleo_meses"] == 6.0


def test_cp04_manejo_muestra_insuficiente(db_session: Session):
    """CP04: Cuando la muestra es menor a 5 registros, informa la advertencia sin fallar ni romper el reporte."""
    # Crear una institución vacía (0 egresados)
    inst_vacia = Institution(
        name=f"Universidad Nueva {uuid.uuid4().hex[:4]}",
        is_tenant=True,
    )
    db_session.add(inst_vacia)
    db_session.flush()

    user = AppUser(
        email=f"admin_vacio_{uuid.uuid4().hex[:6]}@unueva.edu.bo",
        password_hash="fake",
        account_status="active",
        institution_id=inst_vacia.id,
    )
    db_session.add(user)
    db_session.flush()

    role_admin = db_session.query(Role).filter_by(name="platform_admin").first()
    db_session.add(UserRole(user_id=user.id, role_id=role_admin.id))
    db_session.commit()

    token = create_access_token(
        str(user.id),
        "platform_admin",
        extra_claims={"roles": ["platform_admin"], "institution_id": str(inst_vacia.id)},
    )

    # 1. Consultar JSON de tablero: debe advertir muestra_suficiente = False
    r_tablero = client.get("/api/indicators", headers={"Authorization": f"Bearer {token}"})
    assert r_tablero.status_code == 200, r_tablero.text
    data = r_tablero.json()
    assert data["muestra_suficiente"] is False
    assert data["advertencia_muestra"] is not None
    assert "< 5" in data["advertencia_muestra"]
    assert data["tasa_colocacion"] == 0.0

    # 2. Exportar a PDF con muestra insuficiente: debe responder 200 con archivo válido
    r_pdf = client.get(
        "/api/indicators/export",
        headers={"Authorization": f"Bearer {token}"},
        params={"format": "pdf"},
    )
    assert r_pdf.status_code == 200
    assert r_pdf.content.startswith(b"%PDF-")

    # 3. Exportar a Excel con muestra insuficiente: debe responder 200 con archivo válido
    r_xlsx = client.get(
        "/api/indicators/export",
        headers={"Authorization": f"Bearer {token}"},
        params={"format": "xlsx"},
    )
    assert r_xlsx.status_code == 200
    assert r_xlsx.content.startswith(b"PK")

