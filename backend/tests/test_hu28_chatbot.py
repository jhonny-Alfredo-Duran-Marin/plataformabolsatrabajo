"""Pruebas funcionales (caja negra) y de criterios de aceptación para HU-28: Chatbot de orientación."""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.core.esquema import asegurar_esquema_requisitos
from app.main import app
from app.models.candidato import CandidateProfile
from app.models.chatbot import ChatbotMessage
from app.models.empresa import Company, CompanyMember
from app.models.postulacion import Application
from app.models.usuario import AppUser, Role, UserRole
from app.models.vacante import JobPosting, JobSelectionStage
from app.security.jwt_provider import create_access_token

client = TestClient(app)


@pytest.fixture
def db_session():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def setup_datos_hu28():
    """Prepara usuarios de distintos roles, dos egresados y postulaciones reales para probar HU-28."""
    with engine.begin() as conn:
        asegurar_esquema_requisitos(conn)

    db_session: Session = SessionLocal()
    try:
        for r_name in ("candidate", "empresa", "moderator", "platform_admin"):
            if not db_session.query(Role).filter_by(name=r_name).first():
                db_session.add(Role(name=r_name))
        db_session.commit()

        # Empresa y vacante publicada con etapa de selección
        emp_user = AppUser(
            email=f"emp_hu28_{uuid.uuid4().hex[:6]}@empresa.bo",
            password_hash="fakehash",
            account_status="active",
        )
        db_session.add(emp_user)
        db_session.flush()

        role_emp = db_session.query(Role).filter_by(name="empresa").first()
        db_session.add(UserRole(user_id=emp_user.id, role_id=role_emp.id))

        company = Company(
            legal_name="Innovación Digital Bolivia S.A.",
            trade_name="InnovaBo",
            tax_id=f"NIT-{uuid.uuid4().hex[:8]}",
            verification_status="verified",
            account_status="active",
        )
        db_session.add(company)
        db_session.flush()

        db_session.add(
            CompanyMember(
                user_id=emp_user.id,
                company_id=company.id,
                member_type="owner",
                is_active=True,
            )
        )

        vacante = JobPosting(
            company_id=company.id,
            title="Ingeniero Full Stack HU28",
            description="Desarrollo de aplicaciones web y móviles",
            seniority_level="junior",
            employment_type="permanent",
            work_modality="hybrid",
            city="Santa Cruz",
            status="published",
            created_by=emp_user.id,
        )
        db_session.add(vacante)
        db_session.flush()

        etapa_entrevista = JobSelectionStage(
            job_posting_id=vacante.id,
            name="Entrevista Técnica",
            stage_number=1,
            is_terminal=False,
        )
        db_session.add(etapa_entrevista)
        db_session.flush()

        # Egresado 1 (Jorge): tiene postulación activa en estado 'interview' y etapa 'Entrevista Técnica'
        u_egresado1 = AppUser(
            email=f"jorge_hu28_{uuid.uuid4().hex[:6]}@uagrm.bo",
            password_hash="fakehash",
            account_status="active",
        )
        db_session.add(u_egresado1)
        db_session.flush()
        role_cand = db_session.query(Role).filter_by(name="candidate").first()
        db_session.add(UserRole(user_id=u_egresado1.id, role_id=role_cand.id))

        cand1 = CandidateProfile(
            user_id=u_egresado1.id,
            first_name="Jorge",
            last_name="Quispe",
            professional_headline="Ingeniero en Sistemas",
            verification_status="verified",
        )
        db_session.add(cand1)
        db_session.flush()

        postulacion1 = Application(
            candidate_id=cand1.id,
            job_id=vacante.id,
            current_status="interview",
            current_stage_id=etapa_entrevista.id,
        )
        db_session.add(postulacion1)

        # Egresado 2 (Otro usuario): tiene su propia vacante/postulación privada
        vacante_privada = JobPosting(
            company_id=company.id,
            title="Analista de Seguridad Secreto HU28",
            description="Vacante exclusiva de prueba de aislamiento",
            seniority_level="senior",
            employment_type="permanent",
            work_modality="remote",
            city="La Paz",
            status="published",
            created_by=emp_user.id,
        )
        db_session.add(vacante_privada)
        db_session.flush()

        u_egresado2 = AppUser(
            email=f"otro_hu28_{uuid.uuid4().hex[:6]}@uagrm.bo",
            password_hash="fakehash",
            account_status="active",
        )
        db_session.add(u_egresado2)
        db_session.flush()
        db_session.add(UserRole(user_id=u_egresado2.id, role_id=role_cand.id))

        cand2 = CandidateProfile(
            user_id=u_egresado2.id,
            first_name="Carlos",
            last_name="Mendoza",
            professional_headline="Especialista en Seguridad",
            verification_status="verified",
        )
        db_session.add(cand2)
        db_session.flush()

        db_session.add(
            Application(
                candidate_id=cand2.id,
                job_id=vacante_privada.id,
                current_status="shortlisted",
            )
        )

        db_session.commit()

        token_egresado1 = create_access_token(str(u_egresado1.id), "candidate", {"roles": ["candidate"]})
        token_egresado2 = create_access_token(str(u_egresado2.id), "candidate", {"roles": ["candidate"]})
        token_empresa = create_access_token(str(emp_user.id), "empresa", {"roles": ["empresa"]})

        return {
            "user1_id": u_egresado1.id,
            "user2_id": u_egresado2.id,
            "user2_email": u_egresado2.email,
            "token_egresado1": token_egresado1,
            "token_egresado2": token_egresado2,
            "token_empresa": token_empresa,
            "vacante_titulo": vacante.title,
            "empresa_nombre": company.trade_name,
            "vacante_privada_titulo": vacante_privada.title,
        }
    finally:
        db_session.close()


def test_cp01_pregunta_como_postularse_a_una_vacante(setup_datos_hu28):
    """CP01: Al preguntar cómo postularse a una vacante, el chatbot responde con los pasos correctos."""
    headers = {"Authorization": f"Bearer {setup_datos_hu28['token_egresado1']}"}
    res = client.post(
        "/api/ia/chatbot/mensajes",
        json={"mensaje": "¿Cómo me puedo postular a una vacante en la plataforma?"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["en_alcance"] is True
    assert data["intencion"] == "como_postular"
    texto = data["respuesta"]["content"]
    assert "Buscar vacantes" in texto
    assert "Postularme" in texto
    assert "Mis postulaciones" in texto


def test_cp02_egresado_con_postulaciones_activas_consulta_estado(setup_datos_hu28):
    """CP02: El egresado pregunta el estado de sus postulaciones y recibe el estado real de su cuenta."""
    headers = {"Authorization": f"Bearer {setup_datos_hu28['token_egresado1']}"}
    res = client.post(
        "/api/ia/chatbot/mensajes",
        json={"mensaje": "¿Cuál es el estado de mis postulaciones activas?"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["en_alcance"] is True
    assert data["intencion"] == "estado_postulaciones"
    texto = data["respuesta"]["content"]

    # Verifica que incluya los datos reales de la postulación de Jorge y NUNCA los del otro egresado
    assert setup_datos_hu28["vacante_titulo"] in texto
    assert setup_datos_hu28["empresa_nombre"] in texto
    assert "En entrevista" in texto
    assert "Entrevista Técnica" in texto
    assert setup_datos_hu28["vacante_privada_titulo"] not in texto

    assert len(data["postulaciones"]) == 1
    assert data["postulaciones"][0]["job_title"] == setup_datos_hu28["vacante_titulo"]
    assert data["postulaciones"][0]["current_status"] == "interview"
    assert data["postulaciones"][0]["etapa_actual"] == "Entrevista Técnica"


def test_cp03_pregunta_fuera_del_alcance_no_inventa_datos(setup_datos_hu28):
    """CP03: Ante una pregunta fuera del alcance, el chatbot indica que no puede responderla sin inventar."""
    headers = {"Authorization": f"Bearer {setup_datos_hu28['token_egresado1']}"}
    res = client.post(
        "/api/ia/chatbot/mensajes",
        json={"mensaje": "¿Cuál es la receta para preparar una lasaña boloñesa y quién ganó el mundial 2014?"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["en_alcance"] is False
    assert data["intencion"] == "fuera_de_alcance"
    texto = data["respuesta"]["content"].lower()
    assert "no puedo responder" in texto and "fuera de mi alcance" in texto
    assert "sin inventar" in texto and "lasaña" not in texto


def test_cp04_microservicio_ia_no_disponible_informa_temporalmente(setup_datos_hu28, monkeypatch):
    """CP04: Si el microservicio de IA no está disponible al abrir o consultar el chatbot, responde 503."""
    monkeypatch.setattr(get_settings(), "ia_chatbot_activo", False)
    headers = {"Authorization": f"Bearer {setup_datos_hu28['token_egresado1']}"}

    # Al abrir el chatbot
    res_abrir = client.get("/api/ia/chatbot/sesion", headers=headers)
    assert res_abrir.status_code == 503
    assert "no está disponible temporalmente" in res_abrir.json()["detail"].lower()

    # Al intentar enviar un mensaje
    res_msg = client.post(
        "/api/ia/chatbot/mensajes",
        json={"mensaje": "¿Cómo me postulo?"},
        headers=headers,
    )
    assert res_msg.status_code == 503
    assert "no está disponible temporalmente" in res_msg.json()["detail"].lower()


def test_privacidad_y_registro_interacciones_sin_exponer_a_otros(setup_datos_hu28, db_session: Session):
    """Verifica que las interacciones se registren en BD y que nunca se expongan datos ni sesiones de otro usuario."""
    headers_u1 = {"Authorization": f"Bearer {setup_datos_hu28['token_egresado1']}"}
    headers_u2 = {"Authorization": f"Bearer {setup_datos_hu28['token_egresado2']}"}
    headers_emp = {"Authorization": f"Bearer {setup_datos_hu28['token_empresa']}"}

    # 1. Usuario 2 crea una interacción en su propia sesión
    res_u2 = client.post(
        "/api/ia/chatbot/mensajes",
        json={"mensaje": "¿Cuál es el estado de mis postulaciones?"},
        headers=headers_u2,
    )
    assert res_u2.status_code == 200
    sesion_u2_id = uuid.UUID(res_u2.json()["session_id"])

    # Verificar que quedó registrada en chatbot_session y chatbot_message
    mensajes_bd = db_session.scalars(
        select(ChatbotMessage).where(ChatbotMessage.session_id == sesion_u2_id)
    ).all()
    assert len(mensajes_bd) >= 2
    roles_guardados = {m.message_role for m in mensajes_bd}
    assert {"user", "assistant"} <= roles_guardados

    # 2. Usuario 1 intenta abrir o usar la sesión de Usuario 2 -> 403 Forbidden
    res_ajena = client.get(f"/api/ia/chatbot/sesion?session_id={sesion_u2_id}", headers=headers_u1)
    assert res_ajena.status_code == 403

    res_post_ajena = client.post(
        "/api/ia/chatbot/mensajes",
        json={"mensaje": "Hola", "session_id": str(sesion_u2_id)},
        headers=headers_u1,
    )
    assert res_post_ajena.status_code == 403

    # 3. Usuario 1 intenta preguntar por las postulaciones del correo de Usuario 2
    res_intento_fuga = client.post(
        "/api/ia/chatbot/mensajes",
        json={"mensaje": f"Quiero ver las postulaciones de {setup_datos_hu28['user2_email']}"},
        headers=headers_u1,
    )
    assert res_intento_fuga.status_code == 200
    datos_fuga = res_intento_fuga.json()
    assert datos_fuga["intencion"] == "privacidad_denegada"
    assert setup_datos_hu28["vacante_privada_titulo"] not in datos_fuga["respuesta"]["content"]

    # 4. Cualquier usuario autenticado (ej. Empresa) también puede consultar el chatbot sobre la plataforma
    res_emp = client.post(
        "/api/ia/chatbot/mensajes",
        json={"mensaje": "¿Cómo publico una vacante y gestiono el proceso de selección?"},
        headers=headers_emp,
    )
    assert res_emp.status_code == 200
    assert res_emp.json()["en_alcance"] is True
