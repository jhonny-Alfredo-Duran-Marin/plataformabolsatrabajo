"""HU-29: registro de colocaciones (contrataciones de egresados) de cada universidad."""
import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.main import app
from app.models.candidato import CandidateProfile
from app.models.colocacion import Placement
from app.models.empresa import Company, CompanyMember
from app.models.institucion import Institution
from app.models.notificacion import Notification
from app.models.postulacion import Application
from app.models.seguridad import AuditLog
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


def _usuario(db: Session, prefijo: str, rol: str, universidad: uuid.UUID | None = None) -> AppUser:
    if not db.query(Role).filter_by(name=rol).first():
        db.add(Role(name=rol))
        db.flush()
    usuario = AppUser(
        email=f"{prefijo}_{uuid.uuid4().hex[:8]}@test.bo",
        password_hash="x",
        account_status="active",
        institution_id=universidad,
    )
    db.add(usuario)
    db.flush()
    db.add(UserRole(user_id=usuario.id, role_id=db.query(Role).filter_by(name=rol).first().id))
    return usuario


def _egresado(db: Session, universidad: uuid.UUID, nombre: str) -> CandidateProfile:
    usuario = _usuario(db, "egresado", "candidate", universidad)
    perfil = CandidateProfile(
        user_id=usuario.id,
        first_name=nombre,
        last_name="Prueba",
        institution_id=universidad,
        verification_status="verified",
    )
    db.add(perfil)
    db.flush()
    return perfil


def _cabecera(usuario: AppUser, rol: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token(str(usuario.id), rol, {'roles': [rol]})}"}


@pytest.fixture
def escenario(db_session: Session):
    """Dos universidades con su admin y un egresado cada una, una empresa registrada y un superadmin."""
    db = db_session
    sufijo = uuid.uuid4().hex[:6]
    uagrm = Institution(name=f"UAGRM Colocaciones {sufijo}", is_tenant=True, slug=f"ua{sufijo}")
    umss = Institution(name=f"UMSS Colocaciones {sufijo}", is_tenant=True, slug=f"um{sufijo}")
    db.add_all([uagrm, umss])
    db.flush()

    admin_uagrm = _usuario(db, "admin_uagrm", "platform_admin", uagrm.id)
    admin_umss = _usuario(db, "admin_umss", "platform_admin", umss.id)
    moderador = _usuario(db, "mod_uagrm", "moderator", uagrm.id)
    superadmin = _usuario(db, "super", "platform_admin", None)
    de_uagrm = _egresado(db, uagrm.id, f"Ana{sufijo}")
    de_umss = _egresado(db, umss.id, f"Beto{sufijo}")
    empresa = Company(
        legal_name=f"Empresa Colocaciones {sufijo} S.R.L.",
        trade_name=f"Colocaciones {sufijo}",
        tax_id=f"NIT-{uuid.uuid4().hex[:8]}",
        verification_status="verified",
        account_status="active",
    )
    db.add(empresa)
    db.commit()
    return {
        "sufijo": sufijo,
        "uagrm": uagrm.id,
        "umss": umss.id,
        "admin_uagrm": _cabecera(admin_uagrm, "platform_admin"),
        "admin_uagrm_id": admin_uagrm.id,
        "admin_umss": _cabecera(admin_umss, "platform_admin"),
        "admin_umss_id": admin_umss.id,
        "moderador": _cabecera(moderador, "moderator"),
        "superadmin": _cabecera(superadmin, "platform_admin"),
        "de_uagrm": de_uagrm.id,
        "de_umss": de_umss.id,
        "empresa": empresa.id,
    }


def _registrar(e: dict, cabecera: str = "admin_uagrm", **extra):
    cuerpo = {
        "egresado_id": str(e["de_uagrm"]),
        "empresa_id": str(e["empresa"]),
        "cargo": "Analista de datos",
        "fecha_inicio": "2026-03-01",
        **extra,
    }
    return client.post("/api/colocaciones", headers=e[cabecera], json=cuerpo)


def _ids(res) -> list[str]:
    return [item["id"] for item in res.json()["items"]]


def _bitacora(db: Session, accion: str, colocacion_id: str) -> list[AuditLog]:
    db.expire_all()
    return [
        log
        for log in db.query(AuditLog).filter_by(entity_type="colocaciones", action=accion).all()
        if f"colocacion_id={colocacion_id}" in (log.details_json or {}).get("detalle", "")
    ]


# ─── CP01: registro manual ────────────────────────────────────────────────


def test_cp01_registrar_colocacion_manual(escenario, db_session: Session):
    e = escenario
    res = _registrar(e, salario="4500.50", moneda="bob")
    assert res.status_code == 201, res.text
    c = res.json()
    assert c["estado"] == "confirmed" and c["origen"] == "manual" and c["postulacion_id"] is None
    assert c["cargo"] == "Analista de datos" and c["fecha_inicio"] == "2026-03-01"
    assert c["empresa_id"] == str(e["empresa"]) and c["empresa"].startswith("Colocaciones")
    assert c["moneda"] == "BOB" and float(c["salario"]) == 4500.5
    assert c["universidad_id"] == str(e["uagrm"])
    assert len(_bitacora(db_session, "registrar_colocacion", c["id"])) == 1

    # Un egresado puede tener varias colocaciones, y la empresa puede ser un nombre libre.
    otra = _registrar(e, empresa_id=None, empresa_nombre="Taller sin registrar", cargo="Consultor", fecha_inicio="2026-06-01")
    assert otra.status_code == 201, otra.text
    assert otra.json()["empresa_id"] is None and otra.json()["empresa"] == "Taller sin registrar"
    listado = client.get("/api/colocaciones", headers=e["admin_uagrm"], params={"q": f"Ana{e['sufijo']}"})
    assert listado.json()["total"] == 2

    # Idéntica a una existente: se rechaza.
    assert _registrar(e).status_code == 409
    # Faltan datos obligatorios.
    assert _registrar(e, empresa_id=None).status_code == 422
    assert _registrar(e, cargo="").status_code == 422
    assert _registrar(e, salario="100").status_code == 422  # salario sin moneda
    # El moderador no tiene este permiso y un egresado ajeno no existe para este admin.
    assert _registrar(e, "moderador").status_code == 403
    assert _registrar(e, egresado_id=str(e["de_umss"]), cargo="Otro").status_code == 404


# ─── CP02: sugerencia al pasar a «Contratado» ─────────────────────────────


@pytest.fixture
def proceso(escenario, db_session: Session):
    """Postulación del egresado de la UAGRM en una vacante cuya última etapa es «Contratación»."""
    db = db_session
    e = escenario
    empresa_user = _usuario(db, "empresa", "empresa")
    db.add(CompanyMember(user_id=empresa_user.id, company_id=e["empresa"], member_type="recruiter", is_active=True))
    vacante = JobPosting(
        company_id=e["empresa"],
        title="Desarrollador Backend",
        description="Vacante de prueba",
        seniority_level="junior",
        employment_type="permanent",
        work_modality="remote",
        city="Santa Cruz",
        status="published",
        created_by=empresa_user.id,
    )
    db.add(vacante)
    db.flush()
    revision = JobSelectionStage(job_posting_id=vacante.id, stage_number=1, name="Revisión de CV", is_terminal=False)
    contratacion = JobSelectionStage(job_posting_id=vacante.id, stage_number=2, name="Contratación", is_terminal=True)
    db.add_all([revision, contratacion])
    db.flush()
    postulacion = Application(
        candidate_id=e["de_uagrm"], job_id=vacante.id, current_stage_id=revision.id, current_status="screening"
    )
    db.add(postulacion)
    db.commit()
    return {
        "empresa": _cabecera(empresa_user, "empresa"),
        "postulacion": postulacion.id,
        "revision": revision.id,
        "contratacion": contratacion.id,
    }


def _avanzar(p: dict, etapa: str):
    return client.post(
        f"/api/seleccion/postulaciones/{p['postulacion']}/avanzar",
        headers=p["empresa"],
        json={"stage_id": str(p[etapa])},
    )


def _avisos(db: Session, usuario_id: uuid.UUID) -> list[Notification]:
    db.expire_all()
    return db.query(Notification).filter_by(user_id=usuario_id, notification_type="colocacion_sugerida").all()


def test_cp02_sugerencia_al_pasar_a_hired(escenario, proceso, db_session: Session):
    e = escenario
    assert client.get("/api/colocaciones", headers=e["admin_uagrm"]).json()["total"] == 0

    assert _avanzar(proceso, "contratacion").status_code == 200
    db_session.expire_all()
    filas = db_session.query(Placement).filter_by(application_id=proceso["postulacion"]).all()
    assert len(filas) == 1
    c = filas[0]
    assert (c.status, c.source) == ("suggested", "platform")
    assert c.candidate_id == e["de_uagrm"] and c.institution_id == e["uagrm"] and c.company_id == e["empresa"]
    assert c.position_title == "Desarrollador Backend"
    assert len(_avisos(db_session, e["admin_uagrm_id"])) == 1  # avisa a los admins de su universidad
    assert _avisos(db_session, e["admin_umss_id"]) == []

    # Repetir el paso, o volver a pasar por otra etapa y regresar, no duplica la sugerencia.
    assert _avanzar(proceso, "contratacion").status_code == 200
    assert _avanzar(proceso, "revision").status_code == 200
    assert _avanzar(proceso, "contratacion").status_code == 200
    db_session.expire_all()
    assert db_session.query(Placement).filter_by(application_id=proceso["postulacion"]).count() == 1
    assert len(_avisos(db_session, e["admin_uagrm_id"])) == 1

    # Aparece primero en la lista, el contador la cuenta y el admin la confirma.
    listado = client.get("/api/colocaciones", headers=e["admin_uagrm"]).json()
    assert listado["total"] == 1 and listado["sugeridas"] == 1
    assert listado["items"][0]["estado"] == "suggested" and listado["items"][0]["origen"] == "platform"
    confirmada = client.post(f"/api/colocaciones/{c.id}/confirmar", headers=e["admin_uagrm"])
    assert confirmada.status_code == 200, confirmada.text
    assert confirmada.json()["estado"] == "confirmed"
    assert len(_bitacora(db_session, "confirmar_colocacion", str(c.id))) == 1
    assert client.post(f"/api/colocaciones/{c.id}/confirmar", headers=e["admin_uagrm"]).status_code == 409
    assert client.get("/api/colocaciones", headers=e["admin_uagrm"]).json()["sugeridas"] == 0


# ─── CP03: editar con motivo ──────────────────────────────────────────────


def test_cp03_editar_colocacion_con_motivo(escenario, db_session: Session):
    e = escenario
    creada = _registrar(e).json()
    url = f"/api/colocaciones/{creada['id']}"

    # Sin motivo no se edita.
    assert client.put(url, headers=e["admin_uagrm"], json={"cargo": "Jefe de datos"}).status_code == 422
    assert client.put(url, headers=e["admin_uagrm"], json={"cargo": "Jefe de datos", "motivo": " "}).status_code == 422
    # Con el motivo sí, y solo cambia lo enviado.
    res = client.put(
        url,
        headers=e["admin_uagrm"],
        json={"cargo": "Jefe de datos", "fecha_inicio": "2026-04-15", "motivo": "Corrección del contrato"},
    )
    assert res.status_code == 200, res.text
    c = res.json()
    assert c["cargo"] == "Jefe de datos" and c["fecha_inicio"] == "2026-04-15"
    assert c["empresa_id"] == str(e["empresa"]) and c["motivo_ultimo_cambio"] == "Corrección del contrato"
    logs = _bitacora(db_session, "editar_colocacion", creada["id"])
    assert len(logs) == 1 and "Corrección del contrato" in logs[0].details_json["detalle"]
    # Un PUT que no cambia nada, o una colocación de otra universidad, se rechazan.
    assert client.put(url, headers=e["admin_uagrm"], json={"cargo": "Jefe de datos", "motivo": "Nada"}).status_code == 422
    assert client.put(url, headers=e["admin_umss"], json={"cargo": "X de otra", "motivo": "Intento"}).status_code == 404


# ─── CP04: eliminación lógica con motivo ──────────────────────────────────


def test_cp04_eliminar_logico_con_motivo(escenario, db_session: Session):
    e = escenario
    creada = _registrar(e).json()
    url = f"/api/colocaciones/{creada['id']}"

    sin_motivo = client.request("DELETE", url, headers=e["admin_uagrm"], json={})
    assert sin_motivo.status_code == 422
    assert client.request("DELETE", url, headers=e["admin_uagrm"], json={"motivo": "  "}).status_code == 422

    res = client.request("DELETE", url, headers=e["admin_uagrm"], json={"motivo": "Se registró por error"})
    assert res.status_code == 200, res.text
    assert res.json()["estado"] == "cancelled" and res.json()["motivo_eliminacion"] == "Se registró por error"
    # Nunca se borra la fila: queda con su fecha y su motivo.
    db_session.expire_all()
    fila = db_session.get(Placement, uuid.UUID(creada["id"]))
    assert fila is not None and fila.deleted_at is not None and fila.deleted_reason == "Se registró por error"
    assert len(_bitacora(db_session, "eliminar_colocacion", creada["id"])) == 1
    # Deja de verse en la lista normal, se ve al pedir las eliminadas, y ya no se edita ni se repite la baja.
    assert creada["id"] not in _ids(client.get("/api/colocaciones", headers=e["admin_uagrm"]))
    assert creada["id"] in _ids(client.get("/api/colocaciones", headers=e["admin_uagrm"], params={"estado": "cancelled"}))
    assert client.put(url, headers=e["admin_uagrm"], json={"cargo": "Otro", "motivo": "Intento"}).status_code == 409
    assert client.request("DELETE", url, headers=e["admin_uagrm"], json={"motivo": "Otra vez"}).status_code == 409
    # El moderador no tiene el botón de eliminar.
    otra = _registrar(e, cargo="Otro cargo").json()
    assert client.request("DELETE", f"/api/colocaciones/{otra['id']}", headers=e["moderador"], json={"motivo": "x" * 4}).status_code == 403


# ─── Multitenant ──────────────────────────────────────────────────────────


def test_aislamiento_multitenant(escenario):
    e = escenario
    de_uagrm = _registrar(e).json()
    de_umss = _registrar(e, "admin_umss", egresado_id=str(e["de_umss"]), cargo="Contador").json()

    uagrm = client.get("/api/colocaciones", headers=e["admin_uagrm"])
    umss = client.get("/api/colocaciones", headers=e["admin_umss"])
    assert de_uagrm["id"] in _ids(uagrm) and de_umss["id"] not in _ids(uagrm)
    assert de_umss["id"] in _ids(umss) and de_uagrm["id"] not in _ids(umss)
    assert {i["universidad_id"] for i in uagrm.json()["items"]} == {str(e["uagrm"])}

    # El admin de una universidad no toca las colocaciones de la otra.
    url = f"/api/colocaciones/{de_uagrm['id']}"
    assert client.post(f"{url}/confirmar", headers=e["admin_umss"]).status_code == 404
    assert client.request("DELETE", url, headers=e["admin_umss"], json={"motivo": "Intento ajeno"}).status_code == 404
    # Tampoco puede registrar a un egresado de la otra universidad ni buscarlo.
    assert _registrar(e, "admin_umss", cargo="Cruzada").status_code == 404
    buscados = client.get("/api/colocaciones/egresados", headers=e["admin_umss"], params={"q": f"Ana{e['sufijo']}"})
    assert buscados.status_code == 200 and buscados.json() == []

    # El superadmin ve las de todas las universidades.
    ids = _ids(client.get("/api/colocaciones", headers=e["superadmin"], params={"q": e["sufijo"], "page_size": 100}))
    assert de_uagrm["id"] in ids and de_umss["id"] in ids
    assert client.get("/api/colocaciones", headers=e["moderador"]).status_code == 403
