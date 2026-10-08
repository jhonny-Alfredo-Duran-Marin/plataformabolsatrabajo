"""Requisitos generales: bitácora confidencial (3), reportes personalizados (5) y tareas
automáticas diarias con copia de seguridad automática (6)."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.tenancy import INSTITUCION_POR_DEFECTO_ID
from app.features.bitacora.service import BitacoraService
from app.features.respaldos.service import RespaldoService
from app.features.tareas import planificador, tareas
from app.main import app
from app.models.candidato import CandidateProfile, CandidateSkill
from app.models.catalogo import Skill
from app.models.empresa import Company, CompanyMember
from app.models.entrevista import Interview
from app.models.institucion import CompanyInstitution, Institution
from app.models.notificacion import Notification
from app.models.postulacion import Application
from app.models.respaldo import SystemBackup
from app.models.seguridad import AuditLog
from app.models.tarea import ScheduledTaskRun
from app.models.usuario import AppUser, Role, UserRole
from app.models.vacante import JobPosting, JobSkill
from app.security import cifrado_bitacora
from app.security.jwt_provider import create_access_token

client = TestClient(app)
UMSS = uuid.UUID("50000000-0000-0000-0000-000000000002")
CLAVE = "EGRESA-CLAVE-DE-PRUEBA-0001"
CLAVE_PUBLICA = cifrado_bitacora.clave_publica_de(CLAVE)


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


def _token(usuario: AppUser, rol: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token(str(usuario.id), rol, {'roles': [rol]})}"}


@pytest.fixture
def datos(db_session: Session):
    db = db_session
    sufijo = uuid.uuid4().hex[:6]
    empresa = Company(
        legal_name=f"Reportes {sufijo} S.R.L.",
        trade_name=f"Reportes {sufijo}",
        tax_id=f"NIT-{sufijo}",
        verification_status="verified",
        account_status="active",
    )
    db.add(empresa)
    db.flush()
    db.add(CompanyInstitution(company_id=empresa.id, institution_id=INSTITUCION_POR_DEFECTO_ID, status="approved"))
    reclutador = _usuario(db, "rrhh", "empresa")
    db.add(CompanyMember(user_id=reclutador.id, company_id=empresa.id, member_type="recruiter", is_active=True))
    ahora = datetime.now(timezone.utc)
    vigente = JobPosting(
        company_id=empresa.id,
        title=f"Analista {sufijo}",
        description="Vacante de prueba",
        seniority_level="junior",
        employment_type="permanent",
        work_modality="remote",
        city="Santa Cruz",
        status="published",
        published_at=ahora - timedelta(days=2),
        created_by=reclutador.id,
    )
    vencida = JobPosting(
        company_id=empresa.id,
        title=f"Vencida {sufijo}",
        description="Vacante de prueba",
        seniority_level="junior",
        employment_type="permanent",
        work_modality="onsite",
        city="Santa Cruz",
        status="published",
        published_at=ahora - timedelta(days=5),
        application_deadline=ahora - timedelta(days=1),
        created_by=reclutador.id,
    )
    db.add_all([vigente, vencida])
    basica = Institution(name=f"Universidad Básica {sufijo}", is_tenant=True, plan_code="basico")
    db.add(basica)
    db.flush()
    superadmin = _usuario(db, "super", "platform_admin")
    admin_uagrm = _usuario(db, "admin_uagrm", "platform_admin", INSTITUCION_POR_DEFECTO_ID)
    admin_umss = _usuario(db, "admin_umss", "platform_admin", UMSS)
    admin_basica = _usuario(db, "admin_basica", "platform_admin", basica.id)
    egresado = _usuario(db, "egresado", "candidate")
    db.add(CandidateProfile(user_id=egresado.id, first_name="Ana", last_name=f"Reporte{sufijo}", verification_status="verified"))
    db.commit()
    yield {
        "sufijo": sufijo,
        "empresa_id": empresa.id,
        "vigente_id": vigente.id,
        "vencida_id": vencida.id,
        "reclutador_id": reclutador.id,
        "superadmin_id": superadmin.id,
        "admin_uagrm_id": admin_uagrm.id,
        "admin_umss_id": admin_umss.id,
        "empresa": _token(reclutador, "empresa"),
        "superadmin": _token(superadmin, "platform_admin"),
        "admin": _token(admin_uagrm, "platform_admin"),
        "admin_umss": _token(admin_umss, "platform_admin"),
        "admin_basica": _token(admin_basica, "platform_admin"),
        "egresado": _token(egresado, "candidate"),
    }
    # Las vacantes de prueba no quedan publicadas: no deben aparecer en el listado público de otros tests.
    db.rollback()
    db.query(JobPosting).filter(JobPosting.company_id == empresa.id).update({"status": "archived"})
    db.commit()


@pytest.fixture
def bitacora_cifrada(monkeypatch):
    monkeypatch.setattr(get_settings(), "bitacora_clave_publica", CLAVE_PUBLICA)


def _clave(clave: str = CLAVE) -> dict:
    return {"X-Clave-Desarrollador": clave}


# ─── Bitácora confidencial ───────────────────────────────────────────────────


def test_la_base_solo_guarda_la_entrada_cifrada(db_session, datos, bitacora_cifrada):
    modulo = f"prueba_{datos['sufijo']}"
    log = BitacoraService(db_session).registrar(
        modulo=modulo, accion="accion_secreta", usuario_id=datos["admin_uagrm_id"], ip="10.1.2.3", detalles="detalle"
    )
    db_session.commit()
    crudo = db_session.get(AuditLog, log.id)
    assert crudo.payload_cifrado.startswith("v1.")
    assert crudo.user_id is None and crudo.ip_address is None and crudo.details_json is None
    assert crudo.action == crudo.entity_type == "cifrado"
    # La base guarda solo el día; la hora exacta va adentro del cifrado.
    assert (crudo.created_at.hour, crudo.created_at.minute, crudo.created_at.second) == (0, 0, 0)
    assert "accion_secreta" not in crudo.payload_cifrado and "10.1.2.3" not in crudo.payload_cifrado


def test_solo_se_lee_con_la_clave_de_desarrollador(db_session, datos, bitacora_cifrada):
    modulo = f"prueba_{datos['sufijo']}"
    BitacoraService(db_session).registrar(
        modulo=modulo, accion="accion_secreta", usuario_id=datos["admin_uagrm_id"], ip="10.1.2.3"
    )
    db_session.commit()

    sin_clave = client.get("/api/bitacora", params={"modulo": modulo}, headers=datos["superadmin"])
    assert sin_clave.status_code == 423
    mala = client.get("/api/bitacora", params={"modulo": modulo}, headers={**datos["superadmin"], **_clave("otra")})
    assert mala.status_code == 423 and "no es correcta" in mala.json()["detail"]
    assert client.post("/api/bitacora/abrir", json={"clave": "otra"}, headers=datos["superadmin"]).status_code == 423

    assert client.post("/api/bitacora/abrir", json={"clave": CLAVE}, headers=datos["superadmin"]).status_code == 204
    res = client.get("/api/bitacora", params={"modulo": modulo}, headers={**datos["superadmin"], **_clave()})
    assert res.status_code == 200, res.text
    [entrada] = res.json()
    assert entrada["accion"] == "accion_secreta" and entrada["ip"] == "10.1.2.3" and entrada["cifrada"] is True
    assert entrada["usuario_correo"].startswith("admin_uagrm_")

    estado = client.get("/api/bitacora/estado", headers=datos["superadmin"]).json()
    assert estado["cifrada"] is True

    # El intento con la clave incorrecta también quedó registrado (cifrado).
    fallidos = client.get(
        "/api/bitacora",
        params={"accion": "clave_bitacora_incorrecta", "usuario_id": str(datos["superadmin_id"])},
        headers={**datos["superadmin"], **_clave()},
    ).json()
    assert len(fallidos) == 2 and all(f["resultado"] is False for f in fallidos)


def test_cada_universidad_ve_solo_su_actividad(db_session, datos, bitacora_cifrada):
    modulo = f"prueba_{datos['sufijo']}"
    servicio = BitacoraService(db_session)
    servicio.registrar(modulo=modulo, accion="de_uagrm", usuario_id=datos["admin_uagrm_id"])
    servicio.registrar(modulo=modulo, accion="de_umss", usuario_id=datos["admin_umss_id"])
    db_session.commit()

    def acciones(quien: str) -> set[str]:
        res = client.get("/api/bitacora", params={"modulo": modulo}, headers={**datos[quien], **_clave()})
        assert res.status_code == 200, res.text
        return {e["accion"] for e in res.json()}

    assert acciones("admin") == {"de_uagrm"}
    assert acciones("admin_umss") == {"de_umss"}
    assert acciones("superadmin") == {"de_uagrm", "de_umss"}


def test_exportar_la_bitacora_cifrada(db_session, datos, bitacora_cifrada):
    modulo = f"prueba_{datos['sufijo']}"
    BitacoraService(db_session).registrar(modulo=modulo, accion="exportable", usuario_id=datos["admin_uagrm_id"])
    db_session.commit()
    pdf = client.get("/api/bitacora/export/pdf", params={"modulo": modulo}, headers={**datos["superadmin"], **_clave()})
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    excel = client.get("/api/bitacora/export/excel", params={"modulo": modulo}, headers=datos["superadmin"])
    assert excel.status_code == 423


def test_sin_clave_configurada_la_bitacora_funciona_como_antes(db_session, datos, monkeypatch):
    monkeypatch.setattr(get_settings(), "bitacora_clave_publica", None)
    modulo = f"prueba_{datos['sufijo']}"
    log = BitacoraService(db_session).registrar(modulo=modulo, accion="en_claro", usuario_id=datos["admin_uagrm_id"])
    db_session.commit()
    assert db_session.get(AuditLog, log.id).action == "en_claro"
    res = client.get("/api/bitacora", params={"modulo": modulo}, headers=datos["superadmin"])
    assert res.status_code == 200 and [e["accion"] for e in res.json()] == ["en_claro"]


# ─── Tareas automáticas ──────────────────────────────────────────────────────


def test_cierra_las_vacantes_vencidas_y_avisa_a_la_empresa(db_session, datos):
    resumen = tareas.cierre_vacantes(db_session)
    assert "Se cerraron" in resumen
    db_session.expire_all()
    vencida = db_session.get(JobPosting, datos["vencida_id"])
    assert vencida.status == "closed" and vencida.closed_at is not None
    assert db_session.get(JobPosting, datos["vigente_id"]).status == "published"
    aviso = db_session.scalar(
        select(Notification).where(
            Notification.user_id == datos["reclutador_id"], Notification.notification_type == "vacante_cerrada"
        )
    )
    assert aviso is not None and datos["sufijo"] in aviso.title


def test_el_boletin_avisa_solo_las_ofertas_nuevas_que_coinciden(db_session, datos):
    db = db_session
    habilidad = Skill(name=f"Kotlin {datos['sufijo']}", category="Software")
    db.add(habilidad)
    nueva = JobPosting(
        company_id=datos["empresa_id"],
        title=f"Desarrollador Kotlin {datos['sufijo']}",
        description="Vacante del boletín",
        seniority_level="junior",
        employment_type="permanent",
        work_modality="remote",
        city="Santa Cruz",
        status="published",
        published_at=datetime.now(timezone.utc) - timedelta(hours=1),
        created_by=datos["reclutador_id"],
    )
    db.add(nueva)
    db.flush()
    db.add(JobSkill(job_posting_id=nueva.id, skill_id=habilidad.id, importance="required"))
    coincide = _usuario(db, "boletin_si", "candidate")
    no_coincide = _usuario(db, "boletin_no", "candidate")
    perfil = CandidateProfile(user_id=coincide.id, first_name="Sí", last_name="Coincide", verification_status="verified")
    db.add_all([perfil, CandidateProfile(user_id=no_coincide.id, first_name="No", last_name="Coincide", verification_status="verified")])
    db.flush()
    db.add(CandidateSkill(candidate_id=perfil.id, skill_id=habilidad.id))
    db.commit()

    resumen = tareas.boletin_ofertas(db)
    assert "ofertas nuevas" in resumen

    def avisos(usuario_id):
        return db.scalars(
            select(Notification).where(Notification.user_id == usuario_id, Notification.notification_type == "job_match")
        ).all()

    [aviso] = avisos(coincide.id)
    assert aviso.link == "/recomendaciones" and nueva.title in aviso.body and "100% de afinidad" in aviso.body
    assert avisos(no_coincide.id) == []


def test_recordatorios_de_vacantes_por_cerrar_y_entrevistas(db_session, datos):
    db = db_session
    ahora = datetime.now(timezone.utc)
    habilidad = Skill(name=f"Rust {datos['sufijo']}", category="Software")
    db.add(habilidad)
    por_cerrar = JobPosting(
        company_id=datos["empresa_id"],
        title=f"Desarrollador Rust {datos['sufijo']}",
        description="Vacante que cierra pronto",
        seniority_level="junior",
        employment_type="permanent",
        work_modality="remote",
        city="Santa Cruz",
        status="published",
        published_at=ahora - timedelta(days=10),
        application_deadline=ahora + timedelta(hours=6),
        created_by=datos["reclutador_id"],
    )
    db.add(por_cerrar)
    db.flush()
    db.add(JobSkill(job_posting_id=por_cerrar.id, skill_id=habilidad.id, importance="required"))
    afin = _usuario(db, "cierre_afin", "candidate")
    postulado = _usuario(db, "cierre_postulado", "candidate")
    perfil_afin = CandidateProfile(user_id=afin.id, first_name="Ana", last_name="Afín", verification_status="verified")
    perfil_postulado = CandidateProfile(
        user_id=postulado.id, first_name="Pablo", last_name="Postulado", verification_status="verified"
    )
    db.add_all([perfil_afin, perfil_postulado])
    db.flush()
    db.add_all(
        [
            CandidateSkill(candidate_id=perfil_afin.id, skill_id=habilidad.id),
            CandidateSkill(candidate_id=perfil_postulado.id, skill_id=habilidad.id),
        ]
    )
    postulacion = Application(candidate_id=perfil_postulado.id, job_id=por_cerrar.id, current_status="interview")
    db.add(postulacion)
    db.flush()
    entrevista = Interview(
        application_id=postulacion.id,
        scheduled_start=ahora + timedelta(hours=20),
        scheduled_end=ahora + timedelta(hours=21),
        modality="virtual",
        meeting_url="https://meet.example.com/egresa",
        status="confirmed",
        created_by=datos["reclutador_id"],
    )
    db.add(entrevista)
    db.commit()

    resumen = tareas.recordatorios(db)
    assert "cierran en las próximas 24 horas" in resumen

    def avisos(usuario_id, tipo):
        return db.scalars(
            select(Notification).where(Notification.user_id == usuario_id, Notification.notification_type == tipo)
        ).all()

    [aviso_egresado] = avisos(afin.id, "vacante_por_cerrar")
    assert aviso_egresado.link == f"/vacantes/{por_cerrar.id}" and por_cerrar.title in aviso_egresado.body
    # Quien ya se postuló no recibe la «última oportunidad», pero sí el recordatorio de su entrevista.
    assert avisos(postulado.id, "vacante_por_cerrar") == []
    [entrevista_egresado] = avisos(postulado.id, "interview_reminder")
    assert entrevista_egresado.link == f"/postulaciones?entrevista={entrevista.id}"
    assert "virtual" in entrevista_egresado.body

    [cierre_empresa] = avisos(datos["reclutador_id"], "recordatorio_vacante")
    assert por_cerrar.title in cierre_empresa.title and "1 postulación" in cierre_empresa.body
    [entrevista_empresa] = avisos(datos["reclutador_id"], "interview_reminder")
    assert "Pablo Postulado" in entrevista_empresa.title

    # Si la tarea vuelve a correr el mismo día no repite los avisos.
    tareas.recordatorios(db)
    assert len(avisos(afin.id, "vacante_por_cerrar")) == 1
    assert len(avisos(datos["reclutador_id"], "recordatorio_vacante")) == 1
    assert len(avisos(postulado.id, "interview_reminder")) == 1


def test_cada_tarea_corre_una_vez_por_dia_desde_la_hora(db_session):
    clave = f"prueba_{uuid.uuid4().hex[:6]}"
    bolivia = planificador.ZONA_BOLIVIA
    manana = datetime.now(bolivia).replace(hour=10, minute=0, second=0, microsecond=0)
    madrugada = manana.replace(hour=1)
    assert planificador.le_toca(db_session, clave, madrugada) is False  # antes de las 03:00
    assert planificador.le_toca(db_session, clave, manana) is True

    for _ in range(3):
        db_session.add(ScheduledTaskRun(task=clave, trigger="automatico", status="failure", started_at=manana))
    db_session.commit()
    assert planificador.le_toca(db_session, clave, manana) is False  # tres intentos fallidos: hasta mañana

    otra = f"prueba_{uuid.uuid4().hex[:6]}"
    db_session.add(ScheduledTaskRun(task=otra, trigger="manual", status="success", started_at=manana))
    db_session.commit()
    assert planificador.le_toca(db_session, otra, manana) is True  # la manual no reemplaza a la automática
    db_session.add(ScheduledTaskRun(task=otra, trigger="automatico", status="success", started_at=manana))
    db_session.commit()
    assert planificador.le_toca(db_session, otra, manana) is False
    assert planificador.le_toca(db_session, otra, manana + timedelta(days=1)) is True


def test_la_copia_automatica_conserva_solo_las_ultimas(db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(get_settings(), "storage_local_path", str(tmp_path))
    monkeypatch.setattr(get_settings(), "respaldos_automaticos_conservar", 1)
    primera, _ = RespaldoService(db_session).generar_automatico()
    segunda, eliminadas = RespaldoService(db_session).generar_automatico()
    assert eliminadas >= 1
    automaticas = db_session.scalars(select(SystemBackup).where(SystemBackup.kind == "automatica")).all()
    assert [r.id for r in automaticas] == [segunda.id]
    assert segunda.created_by is None and segunda.created_by_email == "Sistema (tarea diaria)"
    assert (tmp_path / "respaldos" / segunda.file_name).is_file()
    assert not (tmp_path / "respaldos" / primera.file_name).exists()


def test_panel_de_tareas_solo_para_el_superadmin(datos):
    assert client.get("/api/admin/tareas", headers=datos["admin"]).status_code == 403
    res = client.get("/api/admin/tareas", headers=datos["superadmin"])
    assert res.status_code == 200, res.text
    assert {t["clave"] for t in res.json()["tareas"]} == {
        "respaldo_diario",
        "cierre_vacantes",
        "boletin_ofertas",
        "recordatorios",
    }

    corrida = client.post("/api/admin/tareas/cierre_vacantes/ejecutar", headers=datos["superadmin"])
    assert corrida.status_code == 200, corrida.text
    assert corrida.json()["estado"] == "success" and corrida.json()["disparador"] == "manual"
    tarea = next(t for t in client.get("/api/admin/tareas", headers=datos["superadmin"]).json()["tareas"] if t["clave"] == "cierre_vacantes")
    assert tarea["ultima"]["id"] == corrida.json()["id"]
    assert client.post("/api/admin/tareas/no_existe/ejecutar", headers=datos["superadmin"]).status_code == 404


# ─── Reportes personalizados ─────────────────────────────────────────────────


def _vista(datos, quien: str, cuerpo: dict, **params):
    return client.post("/api/reportes/vista-previa", json=cuerpo, params=params, headers=datos[quien])


def test_cada_rol_ve_sus_reportes_y_columnas(datos):
    def catalogo(quien: str) -> dict:
        res = client.get("/api/reportes/fuentes", headers=datos[quien])
        assert res.status_code == 200, res.text
        return {f["clave"]: [c["clave"] for c in f["columnas"]] for f in res.json()["fuentes"]}

    superadmin, admin, empresa = catalogo("superadmin"), catalogo("admin"), catalogo("empresa")
    assert set(superadmin) == set(admin) == {"egresados", "empresas", "vacantes", "postulaciones"}
    assert "universidad" in superadmin["egresados"] and "universidad" not in admin["egresados"]
    assert set(empresa) == {"vacantes", "postulaciones"} and "empresa" not in empresa["vacantes"]
    assert client.get("/api/reportes/fuentes", headers=datos["egresado"]).status_code == 403


def test_la_empresa_solo_ve_sus_vacantes(datos):
    res = _vista(datos, "empresa", {"fuente": "vacantes", "columnas": ["titulo", "estado"]})
    assert res.status_code == 200, res.text
    assert res.json()["total"] == 2
    assert {f[0] for f in res.json()["filas"]} == {f"Analista {datos['sufijo']}", f"Vencida {datos['sufijo']}"}
    # Columnas o filtros fuera del catálogo no llegan a la consulta.
    assert _vista(datos, "empresa", {"fuente": "vacantes", "columnas": ["empresa"]}).status_code == 422
    assert _vista(datos, "empresa", {"fuente": "egresados", "columnas": ["nombre"]}).status_code == 404
    assert (
        _vista(datos, "empresa", {"fuente": "vacantes", "columnas": ["titulo"], "filtros": {"title; drop": "x"}}).status_code
        == 422
    )


def test_filtros_columnas_y_orden(datos):
    cuerpo = {
        "fuente": "vacantes",
        "columnas": ["publicada", "titulo", "modalidad"],
        "filtros": {"titulo": datos["sufijo"], "modalidad": ["remote"], "publicada": {"desde": "2020-01-01", "hasta": None}},
        "orden": [{"columna": "titulo", "direccion": "desc"}],
    }
    res = _vista(datos, "superadmin", cuerpo)
    assert res.status_code == 200, res.text
    cuerpo_res = res.json()
    assert [c["clave"] for c in cuerpo_res["columnas"]] == ["publicada", "titulo", "modalidad"]
    assert cuerpo_res["total"] == 1 and cuerpo_res["filas"][0][1:] == [f"Analista {datos['sufijo']}", "Remota"]
    assert any("Modalidad: Remota" in linea for linea in cuerpo_res["descripcion"])

    sin_filtro = _vista(datos, "superadmin", {**cuerpo, "filtros": {"titulo": datos["sufijo"]}}).json()
    assert [f[1] for f in sin_filtro["filas"]] == [f"Vencida {datos['sufijo']}", f"Analista {datos['sufijo']}"]


def test_el_plan_basico_no_incluye_reportes(datos):
    catalogo = client.get("/api/reportes/fuentes", headers=datos["admin_basica"]).json()
    assert catalogo["plan_permite"] is False and "Básico" in catalogo["mensaje_plan"]
    res = _vista(datos, "admin_basica", {"fuente": "egresados", "columnas": ["nombre"]})
    assert res.status_code == 402


@pytest.mark.parametrize(
    ("formato", "tipo", "inicio"),
    [
        ("excel", "spreadsheetml", b"PK"),
        ("pdf", "application/pdf", b"%PDF"),
        ("html", "text/html", b"<!doctype html>"),
    ],
)
def test_exporta_en_cada_formato(datos, formato, tipo, inicio):
    res = client.post(
        "/api/reportes/exportar",
        json={"fuente": "vacantes", "columnas": ["titulo", "estado", "postulaciones"], "formato": formato, "titulo": "Mis vacantes"},
        headers=datos["empresa"],
    )
    assert res.status_code == 200, res.text
    assert tipo in res.headers["content-type"] and res.content.startswith(inicio)
    assert f"reporte-vacantes-" in res.headers["content-disposition"]
    if formato == "html":
        assert "Mis vacantes" in res.text and f"Analista {datos['sufijo']}" in res.text


def test_enviar_por_correo(datos, monkeypatch):
    cuerpo = {
        "fuente": "vacantes",
        "columnas": ["titulo"],
        "formato": "pdf",
        "destinatarios": ["jefe@test.bo", "Jefe@test.bo", "rrhh@test.bo"],
        "mensaje": "Te paso el reporte.",
    }
    monkeypatch.setattr(get_settings(), "smtp_host", None)
    monkeypatch.setattr(get_settings(), "brevo_api_key", None)
    assert client.post("/api/reportes/enviar", json=cuerpo, headers=datos["empresa"]).status_code == 503

    enviados = []

    class SmtpFalso:
        def __init__(self, host, port, timeout):
            self.host = host

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def has_extn(self, _):
            return False

        def login(self, *_):
            pass

        def send_message(self, mensaje):
            enviados.append(mensaje)

    monkeypatch.setattr(get_settings(), "smtp_host", "smtp.test")
    monkeypatch.setattr(get_settings(), "smtp_port", 587)
    monkeypatch.setattr("app.shared.email_service.smtplib.SMTP", SmtpFalso)
    res = client.post("/api/reportes/enviar", json=cuerpo, headers=datos["empresa"])
    assert res.status_code == 200, res.text
    assert res.json()["destinatarios"] == ["jefe@test.bo", "rrhh@test.bo"]
    [mensaje] = enviados
    assert mensaje["To"] == "jefe@test.bo, rrhh@test.bo"
    [adjunto] = list(mensaje.iter_attachments())
    assert adjunto.get_filename().endswith(".pdf") and adjunto.get_content().startswith(b"%PDF")
    assert "Te paso el reporte." in mensaje.get_body(("plain",)).get_content()


def test_los_reportes_quedan_en_la_bitacora(db_session, datos):
    antes = db_session.scalar(select(func.count(AuditLog.id)))
    client.post(
        "/api/reportes/exportar",
        json={"fuente": "vacantes", "columnas": ["titulo"], "formato": "excel"},
        headers=datos["empresa"],
    )
    assert db_session.scalar(select(func.count(AuditLog.id))) == antes + 1
