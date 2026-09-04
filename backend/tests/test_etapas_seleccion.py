import uuid
from datetime import datetime, timezone, timedelta
from app.models.candidato import CandidateProfile
from app.models.catalogo import JobCategory
from app.models.empresa import Company, Sector
from app.models.oferta import JobPosting
from app.models.seleccion import (
    Application,
    ApplicationNote,
    ApplicationStageHistory,
    JobSelectionStage,
    Notification,
)
from app.models.usuario import AppUser
from app.security.jwt_provider import create_access_token


def setup_seleccion_test(db):
    # 1. Sector y Empresa
    sector = Sector(name="Finanzas y Banca")
    db.add(sector)
    db.flush()

    empresa = Company(
        legal_name="Banco Continental S.A.",
        trade_name="Banco Continental",
        tax_id="3040506070",
        sector_id=sector.id,
        city="Santa Cruz de la Sierra",
        verification_status="verified",
        account_status="active",
    )
    db.add(empresa)
    db.flush()

    # 2. Reclutador de Empresa
    user_recruiter = AppUser(
        email="reclutador@continental.bo",
        password_hash="hash123",
        account_status="active",
    )
    db.add(user_recruiter)
    db.flush()

    # 3. Vacante
    vacante = JobPosting(
        company_id=empresa.id,
        title="Oficial de Créditos Junior",
        description="Encargado de análisis de microcréditos y evaluación de clientes.",
        seniority_level="junior",
        employment_type="full_time",
        work_modality="on_site",
        city="Santa Cruz de la Sierra",
        status="published",
        application_deadline=datetime.now(timezone.utc) + timedelta(days=20),
    )
    db.add(vacante)
    db.flush()

    # 4. Etapas iniciales
    etapa1 = JobSelectionStage(job_posting_id=vacante.id, stage_number=1, name="Preselección CV")
    etapa2 = JobSelectionStage(job_posting_id=vacante.id, stage_number=2, name="Entrevista RRHH")
    etapa3 = JobSelectionStage(job_posting_id=vacante.id, stage_number=3, name="Oferta Final", is_terminal=True)
    db.add_all([etapa1, etapa2, etapa3])
    db.flush()

    # 5. Candidato 1
    user_cand1 = AppUser(email="lucia.torres@uagrm.bo", password_hash="hash123", account_status="active")
    db.add(user_cand1)
    db.flush()
    cand1 = CandidateProfile(user_id=user_cand1.id, first_name="Lucía", last_name="Torres", city="Santa Cruz")
    db.add(cand1)
    db.flush()

    app1 = Application(
        candidate_id=cand1.id,
        job_id=vacante.id,
        current_stage_id=etapa1.id,
        current_status="applied",
    )
    db.add(app1)
    db.flush()

    # Historial inicial
    hist1 = ApplicationStageHistory(
        application_id=app1.id,
        stage_id=etapa1.id,
        entered_at=datetime.now(timezone.utc),
        result="pending",
    )
    db.add(hist1)

    # 6. Candidato 2
    user_cand2 = AppUser(email="carlos.rojas@uagrm.bo", password_hash="hash123", account_status="active")
    db.add(user_cand2)
    db.flush()
    cand2 = CandidateProfile(user_id=user_cand2.id, first_name="Carlos", last_name="Rojas", city="Santa Cruz")
    db.add(cand2)
    db.flush()

    app2 = Application(
        candidate_id=cand2.id,
        job_id=vacante.id,
        current_stage_id=etapa1.id,
        current_status="applied",
    )
    db.add(app2)

    db.commit()

    token_recruiter = create_access_token(
        str(user_recruiter.id),
        rol="recruiter",
        extra_claims={"roles": ["recruiter", "empresa"]},
    )

    return {
        "vacante_id": str(vacante.id),
        "etapa1_id": str(etapa1.id),
        "etapa2_id": str(etapa2.id),
        "etapa3_id": str(etapa3.id),
        "app1_id": str(app1.id),
        "app2_id": str(app2.id),
        "user_cand1_id": user_cand1.id,
        "token": token_recruiter,
    }


def test_obtener_tablero_seleccion(client, db):
    datos = setup_seleccion_test(db)
    res = client.get(f"/api/seleccion/vacantes/{datos['vacante_id']}/tablero")
    assert res.status_code == 200
    data = res.json()
    assert data["job_title"] == "Oficial de Créditos Junior"
    assert len(data["columnas"]) == 3
    assert data["total_candidatos"] == 2
    # Ambos candidatos están en la etapa 1
    assert len(data["columnas"][0]["candidatos"]) == 2


def test_configurar_etapas_vacante(client, db):
    datos = setup_seleccion_test(db)
    headers = {"Authorization": f"Bearer {datos['token']}"}

    payload = {
        "etapas": [
            {"stage_number": 1, "name": "Fase 1: Revisión Inicial", "is_terminal": False},
            {"stage_number": 2, "name": "Fase 2: Entrevista y Examen", "is_terminal": False},
            {"stage_number": 3, "name": "Fase 3: Contratación", "is_terminal": True},
        ]
    }

    res = client.put(f"/api/seleccion/vacantes/{datos['vacante_id']}/etapas", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 3
    assert data[0]["name"] == "Fase 1: Revisión Inicial"


def test_mover_candidato_etapa_y_notificacion(client, db):
    datos = setup_seleccion_test(db)
    headers = {"Authorization": f"Bearer {datos['token']}"}

    payload = {
        "nueva_etapa_id": datos["etapa2_id"],
        "observacion": "Excelente perfil académico, pasa a entrevista.",
    }

    res = client.post(f"/api/seleccion/postulaciones/{datos['app1_id']}/mover", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["current_stage_id"] == datos["etapa2_id"]

    # Verificar que se generó la notificación en BD para el usuario egresado
    notif = db.query(Notification).filter(Notification.user_id == datos["user_cand1_id"]).first()
    assert notif is not None
    assert "Entrevista RRHH" in notif.body


def test_bloqueo_candidato_descartado(client, db):
    datos = setup_seleccion_test(db)
    headers = {"Authorization": f"Bearer {datos['token']}"}

    # 1. Descartar candidato 2
    res_desc = client.post(
        f"/api/seleccion/postulaciones/{datos['app2_id']}/descartar",
        json={"motivo": "No cumple con los requisitos de experiencia mínima."},
        headers=headers,
    )
    assert res_desc.status_code == 200
    assert res_desc.json()["current_status"] == "rejected"

    # 2. Intentar mover al candidato descartado -> Debe responder error 422 (BusinessException)
    res_mover = client.post(
        f"/api/seleccion/postulaciones/{datos['app2_id']}/mover",
        json={"nueva_etapa_id": datos["etapa2_id"]},
        headers=headers,
    )
    assert res_mover.status_code == 422
    assert "descartado" in res_mover.json()["detail"].lower()


def test_notas_internas_y_auditoria_historial(client, db):
    datos = setup_seleccion_test(db)
    headers = {"Authorization": f"Bearer {datos['token']}"}

    # 1. Registrar nota interna
    res_nota = client.post(
        f"/api/seleccion/postulaciones/{datos['app1_id']}/notas",
        json={"content": "Nota confidencial: Candidato tiene disponibilidad inmediata."},
        headers=headers,
    )
    assert res_nota.status_code == 201
    assert "disponibilidad inmediata" in res_nota.json()["content"]

    # 2. Consultar notas
    res_get_notas = client.get(f"/api/seleccion/postulaciones/{datos['app1_id']}/notas", headers=headers)
    assert res_get_notas.status_code == 200
    assert len(res_get_notas.json()) == 1

    # 3. Consultar historial de auditoría
    res_hist = client.get(f"/api/seleccion/postulaciones/{datos['app1_id']}/historial", headers=headers)
    assert res_hist.status_code == 200
    data_hist = res_hist.json()
    assert len(data_hist["historial"]) >= 1
    assert data_hist["historial"][0]["stage_name"] == "Preselección CV"

