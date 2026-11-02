"""Pruebas funcionales de caja negra para HU-31: Tablero de indicadores de inserción laboral.

Casos de prueba cubiertos:
- CP01: Colocaciones y encuestas registradas de una carrera -> Se muestran los indicadores calculados para esa carrera.
- CP02: Tablero abierto -> Filtrar por período -> Los indicadores se recalculan para el período seleccionado.
- CP03: Carrera con menos de 5 colocaciones registradas -> El sistema muestra 'sin datos suficientes' en vez de un valor poco representativo.
- CP04: Tablero actualizado -> Consultar la fecha de actualización -> El sistema muestra cuándo se calcularon los datos mostrados.
"""

import uuid
from datetime import date, datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.main import app
from app.models.candidato import CandidateEducation, CandidateProfile, CandidateSkill
from app.models.catalogo import FieldOfStudy, Skill
from app.models.colocacion import Placement
from app.models.encuesta import Survey, SurveyAnswer, SurveyQuestion, SurveyQuestionOption, SurveyResponse
from app.models.institucion import Institution
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


def _crear_usuario_staff(db: Session, universidad_id: uuid.UUID, rol: str = "moderator") -> AppUser:
    if not db.query(Role).filter_by(name=rol).first():
        db.add(Role(name=rol))
        db.flush()
    usuario = AppUser(
        email=f"staff_{uuid.uuid4().hex[:8]}@test.bo",
        password_hash="hash_dummy",
        account_status="active",
        institution_id=universidad_id,
    )
    db.add(usuario)
    db.flush()
    db.add(UserRole(user_id=usuario.id, role_id=db.query(Role).filter_by(name=rol).first().id))
    db.commit()
    return usuario


def _crear_egresado_con_carrera(
    db: Session, universidad_id: uuid.UUID, carrera_id: uuid.UUID, anio_egreso: int = 2025
) -> CandidateProfile:
    user = AppUser(
        email=f"egresado_{uuid.uuid4().hex[:8]}@test.bo",
        password_hash="hash_dummy",
        account_status="active",
        institution_id=universidad_id,
    )
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=db.query(Role).filter_by(name="candidate").first().id))

    perfil = CandidateProfile(
        user_id=user.id,
        first_name="Candidato",
        last_name="Prueba",
        institution_id=universidad_id,
        verification_status="verified",
    )
    db.add(perfil)
    db.flush()

    edu = CandidateEducation(
        candidate_id=perfil.id,
        institution_id=universidad_id,
        field_of_study_id=carrera_id,
        program_name="Ingeniería de Prueba",
        academic_status="graduated",
        graduation_date=date(anio_egreso, 6, 15),
    )
    db.add(edu)
    db.flush()
    return perfil


def _crear_colocacion(
    db: Session, universidad_id: uuid.UUID, candidate_id: uuid.UUID, fecha_inicio: date, cargo: str = "Desarrollador"
) -> Placement:
    col = Placement(
        candidate_id=candidate_id,
        institution_id=universidad_id,
        company_name="Empresa Test",
        position_title=cargo,
        start_date=fecha_inicio,
        status="confirmed",
        source="manual",
    )
    db.add(col)
    db.flush()
    return col


def test_cp03_carrera_con_menos_de_5_colocaciones_muestra_sin_datos_suficientes(db_session: Session):
    """CP03: Carrera con menos de 5 colocaciones registradas -> 'sin datos suficientes'."""
    # 1. Crear institución y carrera
    univ = Institution(name=f"Universidad {uuid.uuid4().hex[:6]}", is_tenant=True)
    db_session.add(univ)
    carrera = FieldOfStudy(name=f"Carrera Poco Poblada {uuid.uuid4().hex[:6]}")
    db_session.add(carrera)
    db_session.commit()

    staff = _crear_usuario_staff(db_session, univ.id)
    token = create_access_token(str(staff.id), "moderator")
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Registrar solo 2 egresados con colocación (< 5)
    for _ in range(2):
        cand = _crear_egresado_con_carrera(db_session, univ.id, carrera.id)
        _crear_colocacion(db_session, univ.id, cand.id, date(2026, 1, 10))
    db_session.commit()

    # 3. Consultar tablero filtrando por esta carrera
    resp = client.get(f"/api/indicadores/tablero?carrera_id={carrera.id}", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["hay_suficientes_datos"] is False
    assert data["mensaje_insuficiente"] is not None
    assert "Sin datos suficientes" in data["mensaje_insuficiente"]
    assert data["tasa_colocacion"] is None
    assert data["total_colocaciones"] == 2


def test_cp01_carrera_con_colocaciones_y_encuestas_calcula_indicadores(db_session: Session):
    """CP01: Colocaciones y encuestas registradas de una carrera -> Indicadores calculados."""
    univ = Institution(name=f"Universidad {uuid.uuid4().hex[:6]}", is_tenant=True)
    db_session.add(univ)
    carrera = FieldOfStudy(name=f"Ingeniería en Sistemas {uuid.uuid4().hex[:6]}")
    db_session.add(carrera)
    db_session.commit()

    staff = _crear_usuario_staff(db_session, univ.id)
    token = create_access_token(str(staff.id), "moderator")
    headers = {"Authorization": f"Bearer {token}"}

    # Crear una habilidad y asociarla
    skill_py = Skill(name=f"Python_{uuid.uuid4().hex[:4]}")
    db_session.add(skill_py)
    db_session.flush()

    # Encuesta laboral (HU-30) con la pregunta de relación con la carrera (escala 1 a 5)
    encuesta = Survey(title="Situación laboral", period="2025", institution_id=univ.id)
    db_session.add(encuesta)
    db_session.flush()
    relacion = SurveyQuestion(
        survey_id=encuesta.id,
        code="relacion_carrera",
        question_text="¿Qué tan relacionado está tu trabajo con tu carrera?",
        question_type="scale",
        position=1,
    )
    db_session.add(relacion)
    db_session.flush()

    # Registrar 6 egresados con colocación (>= 5 para activar métricas)
    for valor in (5, 5, 4, 4, 4, 5):
        cand = _crear_egresado_con_carrera(db_session, univ.id, carrera.id, anio_egreso=2025)
        db_session.add(CandidateSkill(candidate_id=cand.id, skill_id=skill_py.id, proficiency_level="advanced"))
        # inicio 6 meses después
        _crear_colocacion(db_session, univ.id, cand.id, date(2025, 12, 15), cargo="Ingeniero de Software")
        respuesta = SurveyResponse(survey_id=encuesta.id, candidate_id=cand.id)
        db_session.add(respuesta)
        db_session.flush()
        db_session.add(SurveyAnswer(response_id=respuesta.id, question_id=relacion.id, answer_number=valor))
    db_session.commit()

    # Consultar tablero filtrando por la carrera
    resp = client.get(f"/api/indicadores/tablero?carrera_id={carrera.id}", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["hay_suficientes_datos"] is True
    assert data["mensaje_insuficiente"] is None
    assert data["total_colocaciones"] == 6
    assert data["tasa_colocacion"] is not None
    assert data["tasa_colocacion"] > 0
    # Egreso 15/06/2025 -> empleo 15/12/2025
    assert data["tiempo_promedio_primer_empleo_meses"] == 6.0
    # Respuestas 5, 5, 4, 4, 4, 5 -> promedio 4,5 de 5
    assert data["pertinencia_empleo_porcentaje"] == 90.0
    assert len(data["habilidades_demandadas"]) > 0


def test_sin_encuesta_ni_habilidades_no_se_inventan_indicadores(db_session: Session):
    """Con colocaciones pero sin encuesta, fecha de egreso ni habilidades, esos indicadores quedan vacíos."""
    univ = Institution(name=f"Universidad {uuid.uuid4().hex[:6]}", is_tenant=True)
    db_session.add(univ)
    db_session.commit()
    staff = _crear_usuario_staff(db_session, univ.id)
    headers = {"Authorization": f"Bearer {create_access_token(str(staff.id), 'moderator')}"}

    for _ in range(5):
        perfil = _crear_egresado_con_carrera(db_session, univ.id, None, anio_egreso=2025)
        db_session.query(CandidateEducation).filter_by(candidate_id=perfil.id).update({"graduation_date": None})
        _crear_colocacion(db_session, univ.id, perfil.id, date(2025, 12, 15), cargo="Vendedor")
    db_session.commit()

    data = client.get("/api/indicadores/tablero", headers=headers).json()

    assert data["hay_suficientes_datos"] is True
    assert data["tiempo_promedio_primer_empleo_meses"] is None
    assert data["pertinencia_empleo_porcentaje"] is None
    assert data["habilidades_demandadas"] == []


def test_cp02_filtrar_por_periodo_recalcula_indicadores(db_session: Session):
    """CP02: Tablero abierto -> Filtrar por período -> Recalcula los indicadores."""
    univ = Institution(name=f"Universidad {uuid.uuid4().hex[:6]}", is_tenant=True)
    db_session.add(univ)
    carrera = FieldOfStudy(name=f"Ingeniería Industrial {uuid.uuid4().hex[:6]}")
    db_session.add(carrera)
    db_session.commit()

    staff = _crear_usuario_staff(db_session, univ.id)
    token = create_access_token(str(staff.id), "moderator")
    headers = {"Authorization": f"Bearer {token}"}

    # 5 colocaciones en 2025
    for _ in range(5):
        cand25 = _crear_egresado_con_carrera(db_session, univ.id, carrera.id, anio_egreso=2025)
        _crear_colocacion(db_session, univ.id, cand25.id, date(2025, 8, 1))

    # 2 colocaciones en 2026 (< 5)
    for _ in range(2):
        cand26 = _crear_egresado_con_carrera(db_session, univ.id, carrera.id, anio_egreso=2026)
        _crear_colocacion(db_session, univ.id, cand26.id, date(2026, 3, 1))
    db_session.commit()

    # 1. Filtro período 2025: debe tener suficientes datos (5 colocaciones)
    resp25 = client.get(f"/api/indicadores/tablero?carrera_id={carrera.id}&periodo=2025", headers=headers)
    assert resp25.status_code == 200
    data25 = resp25.json()
    assert data25["total_colocaciones"] == 5
    assert data25["hay_suficientes_datos"] is True

    # 2. Filtro período 2026: debe recalculares a 2 colocaciones y dar "Sin datos suficientes"
    resp26 = client.get(f"/api/indicadores/tablero?carrera_id={carrera.id}&periodo=2026", headers=headers)
    assert resp26.status_code == 200
    data26 = resp26.json()
    assert data26["total_colocaciones"] == 2
    assert data26["hay_suficientes_datos"] is False
    assert "Sin datos suficientes" in data26["mensaje_insuficiente"]


def test_cp04_muestra_fecha_actualizacion_de_datos(db_session: Session):
    """CP04: Tablero actualizado -> Consultar la fecha de actualización -> Muestra timestamp exacto."""
    univ = Institution(name=f"Universidad {uuid.uuid4().hex[:6]}", is_tenant=True)
    db_session.add(univ)
    db_session.commit()

    staff = _crear_usuario_staff(db_session, univ.id)
    token = create_access_token(str(staff.id), "moderator")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/indicadores/tablero", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "fecha_actualizacion" in data
    assert data["fecha_actualizacion"] is not None
    # Parsear ISO 8601
    dt = datetime.fromisoformat(data["fecha_actualizacion"].replace("Z", "+00:00"))
    assert dt <= datetime.now(timezone.utc)
