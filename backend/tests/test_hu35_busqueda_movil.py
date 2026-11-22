"""HU-35 — Búsqueda y postulación móvil (mismos servicios y reglas de negocio que la web).

Casos de prueba funcionales (caja negra):
- CP01: Búsqueda por palabra clave con filtros (ciudad, modalidad, carrera) y consulta de filtros disponibles.
- CP02: Postulación a una vacante con perfil completo verificado y confirmación + aparición en seguimiento (móvil y web).
- CP03: Postulación repetida a la misma vacante -> el sistema informa que ya existe y no duplica.
- CP04: Reintento tras pérdida de conexión durante la postulación -> garantiza idempotencia sin duplicar registros.
"""

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.tenancy import INSTITUCION_POR_DEFECTO_ID
from app.main import app
from app.models.candidato import CandidateProfile
from app.models.catalogo import FieldOfStudy
from app.models.empresa import Company, CompanyMember
from app.models.institucion import CompanyInstitution
from app.models.postulacion import Application, ApplicationAnswer, ApplicationStatusHistory
from app.models.usuario import AppUser, Role, UserRole
from app.models.vacante import JobEducationPreference, JobPosting, ScreeningOption, ScreeningQuestion
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
def datos_hu35(db_session: Session):
    db = db_session
    sufijo = uuid.uuid4().hex[:6]

    for r_name in ("empresa", "candidate"):
        if not db.query(Role).filter_by(name=r_name).first():
            db.add(Role(name=r_name))
    db.flush()

    empresa_user = AppUser(
        email=f"emp_hu35_{sufijo}@test.bo",
        password_hash="fakehash",
        account_status="active",
    )
    cand_user = AppUser(
        email=f"cand_hu35_{sufijo}@test.bo",
        password_hash="fakehash",
        account_status="active",
    )
    db.add_all([empresa_user, cand_user])
    db.flush()

    role_emp = db.query(Role).filter_by(name="empresa").first()
    role_cand = db.query(Role).filter_by(name="candidate").first()
    db.add_all([
        UserRole(user_id=empresa_user.id, role_id=role_emp.id),
        UserRole(user_id=cand_user.id, role_id=role_cand.id),
    ])

    company = Company(
        legal_name=f"MovilTech HU35 {sufijo} SRL",
        trade_name=f"MovilTech {sufijo}",
        tax_id=f"NIT35-{sufijo}",
        contact_email=f"rrhh_{sufijo}@moviltech.bo",
        city="Santa Cruz",
        verification_status="verified",
        account_status="active",
    )
    db.add(company)
    db.flush()

    db.add(
        CompanyMember(
            user_id=empresa_user.id,
            company_id=company.id,
            member_type="owner",
            job_title="RRHH",
            is_active=True,
        )
    )
    db.add(
        CompanyInstitution(
            company_id=company.id,
            institution_id=INSTITUCION_POR_DEFECTO_ID,
            status="approved",
        )
    )

    candidate = CandidateProfile(
        user_id=cand_user.id,
        institution_id=INSTITUCION_POR_DEFECTO_ID,
        first_name="Jorge",
        last_name="Quispe",
        verification_status="verified",
    )
    db.add(candidate)

    carrera = FieldOfStudy(name=f"Ingeniería Móvil HU35 {sufijo}", category="Tecnología")
    db.add(carrera)
    db.flush()

    vacante_scz = JobPosting(
        company_id=company.id,
        title=f"Desarrollador Flutter Python {sufijo}",
        description="Desarrollo móvil y APIs REST para plataforma universitaria",
        seniority_level="junior",
        employment_type="permanent",
        work_modality="remote",
        city="Santa Cruz",
        status="published",
        published_at=datetime.now(timezone.utc),
        created_by=empresa_user.id,
    )
    vacante_lpz = JobPosting(
        company_id=company.id,
        title=f"Desarrollador Flutter Python {sufijo}",
        description="Mismo puesto pero presencial en La Paz",
        seniority_level="junior",
        employment_type="permanent",
        work_modality="onsite",
        city="La Paz",
        status="published",
        published_at=datetime.now(timezone.utc),
        created_by=empresa_user.id,
    )
    db.add_all([vacante_scz, vacante_lpz])
    db.flush()

    db.add(
        JobEducationPreference(
            job_posting_id=vacante_scz.id,
            field_of_study_id=carrera.id,
            is_required=True,
        )
    )

    pregunta = ScreeningQuestion(
        job_posting_id=vacante_scz.id,
        question_text="¿Tenés experiencia con Flutter?",
        question_type="single_choice",
        is_required=True,
        is_knockout=True,
        position=0,
    )
    db.add(pregunta)
    db.flush()

    opcion_si = ScreeningOption(question_id=pregunta.id, option_text="Sí", is_accepted=True, position=0)
    opcion_no = ScreeningOption(question_id=pregunta.id, option_text="No", is_accepted=False, position=1)
    db.add_all([opcion_si, opcion_no])
    db.commit()

    token_cand = create_access_token(str(cand_user.id), "candidate", {"roles": ["candidate"]})
    headers = {"Authorization": f"Bearer {token_cand}"}

    yield {
        "sufijo": sufijo,
        "headers": headers,
        "candidate": candidate,
        "carrera": carrera,
        "vacante_scz": vacante_scz,
        "vacante_lpz": vacante_lpz,
        "pregunta": pregunta,
        "opcion_si": opcion_si,
    }

    # Limpieza ordenada de los registros creados en la prueba
    apps = db.query(Application).filter(Application.candidate_id == candidate.id).all()
    app_ids = [a.id for a in apps]
    if app_ids:
        db.query(ApplicationAnswer).filter(ApplicationAnswer.application_id.in_(app_ids)).delete(synchronize_session=False)
        db.query(ApplicationStatusHistory).filter(ApplicationStatusHistory.application_id.in_(app_ids)).delete(
            synchronize_session=False
        )
        db.query(Application).filter(Application.id.in_(app_ids)).delete(synchronize_session=False)
    db.query(ScreeningOption).filter(ScreeningOption.question_id == pregunta.id).delete(synchronize_session=False)
    db.query(ScreeningQuestion).filter(ScreeningQuestion.id == pregunta.id).delete(synchronize_session=False)
    db.query(JobEducationPreference).filter(JobEducationPreference.job_posting_id == vacante_scz.id).delete(
        synchronize_session=False
    )
    db.query(JobPosting).filter(JobPosting.id.in_([vacante_scz.id, vacante_lpz.id])).delete(synchronize_session=False)
    db.query(FieldOfStudy).filter(FieldOfStudy.id == carrera.id).delete(synchronize_session=False)
    db.query(CandidateProfile).filter(CandidateProfile.id == candidate.id).delete(synchronize_session=False)
    db.query(CompanyInstitution).filter(CompanyInstitution.company_id == company.id).delete(synchronize_session=False)
    db.query(CompanyMember).filter(CompanyMember.company_id == company.id).delete(synchronize_session=False)
    db.query(Company).filter(Company.id == company.id).delete(synchronize_session=False)
    db.query(UserRole).filter(UserRole.user_id.in_([empresa_user.id, cand_user.id])).delete(synchronize_session=False)
    db.query(AppUser).filter(AppUser.id.in_([empresa_user.id, cand_user.id])).delete(synchronize_session=False)
    db.commit()


def test_cp01_busqueda_movil_por_palabra_clave_y_filtros(datos_hu35):
    """CP01: Búsqueda por palabra clave combinada con ciudad, modalidad y carrera."""
    headers = datos_hu35["headers"]
    sufijo = datos_hu35["sufijo"]
    carrera = datos_hu35["carrera"]
    vacante_scz = datos_hu35["vacante_scz"]

    resp_filtros = client.get("/api/vacantes/buscar/filtros")
    assert resp_filtros.status_code == 200
    filtros = resp_filtros.json()
    assert "ciudades" in filtros and "modalidades" in filtros and "carreras" in filtros

    resp = client.get(
        "/api/vacantes/buscar",
        params={
            "q": f"Flutter Python {sufijo}",
            "ciudad": "Santa Cruz",
            "modalidad": "remote",
            "carrera_id": str(carrera.id),
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == str(vacante_scz.id)
    assert data["items"][0]["city"] == "Santa Cruz"
    assert data["items"][0]["work_modality"] == "remote"


def test_cp02_cp03_cp04_postulacion_movil_duplicado_y_seguimiento_web_movil(datos_hu35, db_session: Session):
    """CP02, CP03 y CP04: Postulación móvil confirmada, visibilidad en seguimiento web/móvil y bloqueo de duplicado/reintento."""
    headers = datos_hu35["headers"]
    vacante = datos_hu35["vacante_scz"]
    pregunta = datos_hu35["pregunta"]
    opcion_si = datos_hu35["opcion_si"]
    candidate = datos_hu35["candidate"]

    # Preguntas de filtro consumidas por PostulacionScreen
    resp_preg = client.get(f"/api/vacantes/{vacante.id}/preguntas", headers=headers)
    assert resp_preg.status_code == 200
    assert len(resp_preg.json()) == 1

    payload = {
        "job_id": str(vacante.id),
        "answers": [
            {
                "question_id": str(pregunta.id),
                "selected_option_id": str(opcion_si.id),
            }
        ],
    }

    # CP02: Primera postulación desde el móvil -> éxito
    resp_ok = client.post("/api/postulaciones/", json=payload, headers=headers)
    assert resp_ok.status_code == 200
    body_ok = resp_ok.json()
    assert body_ok["current_status"] == "applied"
    assert body_ok["job_id"] == str(vacante.id)

    # Criterio 4: Aparece en el seguimiento compartido de móvil y web
    resp_simple = client.get("/api/postulaciones/", headers=headers)
    assert resp_simple.status_code == 200
    assert any(p["job_id"] == str(vacante.id) for p in resp_simple.json())

    resp_seguimiento = client.get("/api/postulaciones/mis-postulaciones", headers=headers)
    assert resp_seguimiento.status_code == 200
    resumen = resp_seguimiento.json()
    assert resumen["total"] >= 1
    assert any(p["job_id"] == str(vacante.id) for p in resumen["postulaciones"])

    # CP03 y CP04 (reintento cuando ya llegó al servidor): no duplica y responde 400 legible
    resp_dup = client.post("/api/postulaciones/", json=payload, headers=headers)
    assert resp_dup.status_code == 400
    assert "Ya te has postulado" in resp_dup.json()["detail"]

    total_en_bd = (
        db_session.query(Application)
        .filter(Application.candidate_id == candidate.id, Application.job_id == vacante.id)
        .count()
    )
    assert total_en_bd == 1
