"""HU-30: encuesta periódica de situación laboral de los egresados."""
import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.main import app
from app.models.candidato import CandidateEducation, CandidateProfile
from app.models.catalogo import FieldOfStudy
from app.models.encuesta import SurveyAnswer, SurveyResponse
from app.models.institucion import Institution
from app.models.notificacion import Notification
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


def _egresado(db: Session, universidad: uuid.UUID, carrera: FieldOfStudy, validado: bool = True) -> AppUser:
    usuario = _usuario(db, "egresado", "candidate", universidad)
    perfil = CandidateProfile(
        user_id=usuario.id,
        first_name="Egresado",
        last_name="Prueba",
        institution_id=universidad,
        verification_status="verified" if validado else "pending",
    )
    db.add(perfil)
    db.flush()
    db.add(
        CandidateEducation(
            candidate_id=perfil.id,
            institution_id=universidad,
            field_of_study_id=carrera.id,
            program_name=carrera.name,
            academic_status="graduated",
        )
    )
    return usuario


def _cabecera(usuario: AppUser, rol: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token(str(usuario.id), rol, {'roles': [rol]})}"}


@pytest.fixture
def escenario(db_session: Session):
    """Una universidad con dos carreras y egresados de cada tipo, más otra universidad aparte."""
    db = db_session
    sufijo = uuid.uuid4().hex[:6]
    uni = Institution(name=f"Universidad Encuestas {sufijo}", is_tenant=True, slug=f"enc{sufijo}")
    otra = Institution(name=f"Otra Universidad {sufijo}", is_tenant=True, slug=f"otr{sufijo}")
    db.add_all([uni, otra])
    db.flush()
    sistemas = FieldOfStudy(name=f"Sistemas {sufijo}")
    civil = FieldOfStudy(name=f"Civil {sufijo}")
    db.add_all([sistemas, civil])
    db.flush()

    admin = _usuario(db, "admin", "platform_admin", uni.id)
    moderador = _usuario(db, "mod", "moderator", uni.id)
    admin_otra = _usuario(db, "admin_otra", "platform_admin", otra.id)
    de_sistemas = _egresado(db, uni.id, sistemas)
    de_civil = _egresado(db, uni.id, civil)
    sin_validar = _egresado(db, uni.id, sistemas, validado=False)
    de_otra = _egresado(db, otra.id, sistemas)
    db.commit()
    return {
        "uni": uni.id,
        "sistemas": sistemas.id,
        "civil": civil.id,
        "admin": _cabecera(admin, "platform_admin"),
        "moderador": _cabecera(moderador, "moderator"),
        "admin_otra": _cabecera(admin_otra, "platform_admin"),
        "sistemas_id": de_sistemas.id,
        "civil_id": de_civil.id,
        "sistemas_h": _cabecera(de_sistemas, "candidate"),
        "civil_h": _cabecera(de_civil, "candidate"),
        "sin_validar_h": _cabecera(sin_validar, "candidate"),
        "de_otra_h": _cabecera(de_otra, "candidate"),
    }


def _enviar(e: dict, periodo: str = "2026-1", **extra):
    return client.post(
        "/api/encuestas",
        headers=e["admin"],
        json={"titulo": f"Situación laboral {periodo}", "periodo": periodo, **extra},
    )


def _formulario(e: dict, encuesta_id: str, cabecera: str = "sistemas_h") -> dict:
    res = client.get(f"/api/encuestas/{encuesta_id}/formulario", headers=e[cabecera])
    assert res.status_code == 200, res.text
    return res.json()


def _respuestas(formulario: dict, situacion: str, **resto) -> list[dict]:
    """Arma las respuestas por código de pregunta: la situación por el código de su opción."""
    por_codigo = {p["codigo"]: p for p in formulario["preguntas"]}
    opcion = next(o for o in por_codigo["situacion_laboral"]["opciones"] if o["codigo"] == situacion)
    salida = [{"pregunta_id": por_codigo["situacion_laboral"]["id"], "opcion_id": opcion["id"]}]
    for codigo, valor in resto.items():
        campo = "texto" if isinstance(valor, str) else "numero"
        salida.append({"pregunta_id": por_codigo[codigo]["id"], campo: valor})
    return salida


def _trabaja(formulario: dict) -> list[dict]:
    return _respuestas(
        formulario, "empleado", empresa="TecnoSur", cargo="Desarrollador", relacion_carrera=5, meses_primer_empleo=3
    )


def _avisos(db: Session, usuario_id: uuid.UUID) -> list[Notification]:
    db.expire_all()
    return db.query(Notification).filter_by(user_id=usuario_id, notification_type="encuesta_laboral").all()


# ─── CP01: configurar y enviar ───────────────────────────────────────────


def test_la_encuesta_llega_a_los_egresados_validados_de_la_universidad(escenario, db_session):
    res = _enviar(escenario, vence_el=(date.today() + timedelta(days=10)).isoformat())
    assert res.status_code == 201, res.text
    encuesta = res.json()["encuesta"]
    # Solo los dos egresados validados de la universidad: no el pendiente ni el de otra universidad.
    assert encuesta["destinatarios"] == 2
    assert encuesta["alcance"] == "universidad" and encuesta["abierta"] is True

    for nombre in ("sistemas_h", "civil_h"):
        pendientes = client.get("/api/encuestas/mias", headers=escenario[nombre]).json()
        assert [p["id"] for p in pendientes] == [encuesta["id"]] and pendientes[0]["respondida"] is False
    assert client.get("/api/encuestas/mias", headers=escenario["sin_validar_h"]).json() == []
    assert client.get("/api/encuestas/mias", headers=escenario["de_otra_h"]).json() == []

    # El aviso sale por la campanita, con enlace a la encuesta.
    avisos = _avisos(db_session, escenario["sistemas_id"])
    assert len(avisos) == 1 and avisos[0].link == f"/encuestas/{encuesta['id']}"
    assert len(_avisos(db_session, escenario["civil_id"])) == 1


def test_enviada_a_una_carrera_solo_la_reciben_sus_egresados(escenario, db_session):
    res = _enviar(escenario, carrera_id=str(escenario["sistemas"]))
    assert res.status_code == 201, res.text
    encuesta = res.json()["encuesta"]
    assert encuesta["destinatarios"] == 1 and encuesta["alcance"] == "carrera" and "Sistemas" in encuesta["carrera"]

    assert [p["id"] for p in client.get("/api/encuestas/mias", headers=escenario["sistemas_h"]).json()] == [
        encuesta["id"]
    ]
    assert client.get("/api/encuestas/mias", headers=escenario["civil_h"]).json() == []
    assert len(_avisos(db_session, escenario["civil_id"])) == 0
    # Una encuesta que no le corresponde se comporta como si no existiera.
    assert client.get(f"/api/encuestas/{encuesta['id']}/formulario", headers=escenario["civil_h"]).status_code == 404


def test_no_se_envia_si_no_hay_a_quien(escenario):
    res = _enviar(escenario, carrera_id=str(uuid.uuid4()))
    assert res.status_code == 404
    vacia = client.post(
        "/api/encuestas",
        headers=escenario["admin_otra"],
        json={"titulo": "Sin gente", "periodo": "2026-1", "carrera_id": str(escenario["civil"])},
    )
    assert vacia.status_code == 422 and "No hay egresados" in vacia.json()["detail"]


def test_la_fecha_de_cierre_tiene_que_ser_futura_y_el_periodo_no_se_repite(escenario):
    pasada = _enviar(escenario, vence_el=(date.today() - timedelta(days=1)).isoformat())
    assert pasada.status_code == 422
    assert _enviar(escenario, "2026-1").status_code == 201
    repetida = _enviar(escenario, "2026-1")
    assert repetida.status_code == 409
    # Otra carrera o otro período sí pueden salir.
    assert _enviar(escenario, "2026-1", carrera_id=str(escenario["sistemas"])).status_code == 201
    assert _enviar(escenario, "2026-2").status_code == 201


# ─── CP02: responder ─────────────────────────────────────────────────────


def test_el_egresado_responde_y_queda_registrado_con_fecha_y_periodo(escenario):
    encuesta = _enviar(escenario).json()["encuesta"]
    formulario = _formulario(escenario, encuesta["id"])
    assert formulario["periodo"] == "2026-1"
    assert [p["codigo"] for p in formulario["preguntas"]] == [
        "situacion_laboral",
        "empresa",
        "cargo",
        "relacion_carrera",
        "meses_primer_empleo",
    ]

    res = client.post(
        f"/api/encuestas/{encuesta['id']}/respuestas",
        headers=escenario["sistemas_h"],
        json={"respuestas": _trabaja(formulario)},
    )
    assert res.status_code == 201, res.text
    assert res.json()["respondida_el"]

    mia = client.get("/api/encuestas/mias", headers=escenario["sistemas_h"]).json()[0]
    assert mia["respondida"] is True and mia["respondida_el"]


def test_las_respuestas_se_validan_contra_las_preguntas(escenario):
    encuesta = _enviar(escenario).json()["encuesta"]
    formulario = _formulario(escenario, encuesta["id"])
    url = f"/api/encuestas/{encuesta['id']}/respuestas"

    def enviar(respuestas):
        return client.post(url, headers=escenario["sistemas_h"], json={"respuestas": respuestas})

    # La situación laboral es obligatoria.
    assert enviar([]).status_code == 422
    # Quien trabaja tiene que decir dónde, en qué y qué tan relacionado está con su carrera.
    sin_empresa = enviar(_respuestas(formulario, "empleado", cargo="Analista", relacion_carrera=4))
    assert sin_empresa.status_code == 422 and "empresa" in sin_empresa.json()["detail"].lower()
    # La relación con la carrera va de 1 a 5 y los meses no pueden ser negativos.
    fuera = enviar(_respuestas(formulario, "empleado", empresa="X", cargo="Y", relacion_carrera=9))
    assert fuera.status_code == 422
    negativos = enviar(
        _respuestas(formulario, "empleado", empresa="X", cargo="Y", relacion_carrera=3, meses_primer_empleo=-2)
    )
    assert negativos.status_code == 422
    # Una pregunta ajena a la encuesta no vale.
    assert enviar([{"pregunta_id": str(uuid.uuid4()), "texto": "hola"}]).status_code == 422
    # Después de tantos intentos fallidos, la respuesta correcta entra: nada quedó a medias.
    assert enviar(_trabaja(formulario)).status_code == 201


def test_quien_no_trabaja_no_declara_empresa_ni_cargo(escenario, db_session):
    encuesta = _enviar(escenario).json()["encuesta"]
    formulario = _formulario(escenario, encuesta["id"], "civil_h")
    res = client.post(
        f"/api/encuestas/{encuesta['id']}/respuestas",
        headers=escenario["civil_h"],
        json={"respuestas": _respuestas(formulario, "buscando", empresa="No corresponde", cargo="No corresponde")},
    )
    assert res.status_code == 201, res.text

    db_session.expire_all()
    respuesta = db_session.query(SurveyResponse).filter_by(survey_id=uuid.UUID(encuesta["id"])).one()
    assert db_session.query(SurveyAnswer).filter_by(response_id=respuesta.id).count() == 1


# ─── CP04: una sola respuesta por período ────────────────────────────────


def test_no_se_responde_dos_veces_el_mismo_periodo_pero_si_otro(escenario):
    primera = _enviar(escenario, "2026-1").json()["encuesta"]
    formulario = _formulario(escenario, primera["id"])
    url = f"/api/encuestas/{primera['id']}/respuestas"
    cuerpo = {"respuestas": _trabaja(formulario)}
    assert client.post(url, headers=escenario["sistemas_h"], json=cuerpo).status_code == 201
    segunda_vez = client.post(url, headers=escenario["sistemas_h"], json=cuerpo)
    assert segunda_vez.status_code == 409 and "Ya respondiste" in segunda_vez.json()["detail"]
    assert client.get(f"/api/encuestas/{primera['id']}/formulario", headers=escenario["sistemas_h"]).status_code == 409

    # Un período nuevo es otra encuesta y se puede responder de nuevo.
    nueva = _enviar(escenario, "2026-2").json()["encuesta"]
    formulario_nuevo = _formulario(escenario, nueva["id"])
    res = client.post(
        f"/api/encuestas/{nueva['id']}/respuestas",
        headers=escenario["sistemas_h"],
        json={"respuestas": _respuestas(formulario_nuevo, "posgrado")},
    )
    assert res.status_code == 201, res.text


# ─── CP03: avance del administrador ──────────────────────────────────────


def test_el_administrador_ve_el_porcentaje_de_respuesta_y_el_reparto(escenario):
    encuesta = _enviar(escenario).json()["encuesta"]
    assert encuesta["respondieron"] == 0 and encuesta["porcentaje"] == 0
    formulario = _formulario(escenario, encuesta["id"])
    client.post(
        f"/api/encuestas/{encuesta['id']}/respuestas",
        headers=escenario["sistemas_h"],
        json={"respuestas": _trabaja(formulario)},
    )

    avance = client.get(f"/api/encuestas/{encuesta['id']}/avance", headers=escenario["admin"]).json()
    assert avance["encuesta"]["respondieron"] == 1 and avance["encuesta"]["destinatarios"] == 2
    assert avance["encuesta"]["porcentaje"] == 50.0 and avance["pendientes"] == 1
    reparto = {s["codigo"]: s["cantidad"] for s in avance["situacion_laboral"]}
    assert reparto == {"empleado": 1, "independiente": 0, "posgrado": 0, "buscando": 0, "sin_buscar": 0}

    listado = client.get("/api/encuestas", headers=escenario["admin"]).json()
    assert listado["total"] == 1 and listado["items"][0]["porcentaje"] == 50.0


# ─── Cierre ──────────────────────────────────────────────────────────────


def test_al_cerrar_la_encuesta_ya_no_se_responde_pero_quien_respondio_la_sigue_viendo(escenario):
    encuesta = _enviar(escenario).json()["encuesta"]
    formulario = _formulario(escenario, encuesta["id"])
    client.post(
        f"/api/encuestas/{encuesta['id']}/respuestas",
        headers=escenario["sistemas_h"],
        json={"respuestas": _trabaja(formulario)},
    )

    cerrada = client.post(f"/api/encuestas/{encuesta['id']}/cerrar", headers=escenario["admin"])
    assert cerrada.status_code == 200 and cerrada.json()["abierta"] is False
    assert client.post(f"/api/encuestas/{encuesta['id']}/cerrar", headers=escenario["admin"]).status_code == 422

    intento = client.post(
        f"/api/encuestas/{encuesta['id']}/respuestas",
        headers=escenario["civil_h"],
        json={"respuestas": _trabaja(formulario)},
    )
    assert intento.status_code == 422 and "cerrada" in intento.json()["detail"]
    assert client.get("/api/encuestas/mias", headers=escenario["civil_h"]).json() == []
    assert [e["respondida"] for e in client.get("/api/encuestas/mias", headers=escenario["sistemas_h"]).json()] == [True]
    # Cerrada, el mismo período puede volver a abrirse.
    assert _enviar(escenario, "2026-1").status_code == 201


# ─── Aislamiento entre universidades y permisos ──────────────────────────


def test_una_universidad_no_ve_ni_toca_las_encuestas_de_otra(escenario):
    encuesta = _enviar(escenario).json()["encuesta"]
    assert client.get("/api/encuestas", headers=escenario["admin_otra"]).json()["total"] == 0
    assert client.get(f"/api/encuestas/{encuesta['id']}/avance", headers=escenario["admin_otra"]).status_code == 404
    assert client.post(f"/api/encuestas/{encuesta['id']}/cerrar", headers=escenario["admin_otra"]).status_code == 404
    assert client.get(f"/api/encuestas/{encuesta['id']}/formulario", headers=escenario["de_otra_h"]).status_code == 404
    otra = client.post(
        f"/api/encuestas/{encuesta['id']}/respuestas",
        headers=escenario["de_otra_h"],
        json={"respuestas": []},
    )
    assert otra.status_code == 404


def test_solo_el_administrador_envia_y_solo_el_egresado_responde(escenario):
    encuesta = _enviar(escenario).json()["encuesta"]
    # El moderador sigue la encuesta, pero no la configura ni la cierra.
    assert client.get("/api/encuestas", headers=escenario["moderador"]).status_code == 200
    assert (
        client.post(
            "/api/encuestas", headers=escenario["moderador"], json={"titulo": "No puede", "periodo": "X"}
        ).status_code
        == 403
    )
    assert client.post(f"/api/encuestas/{encuesta['id']}/cerrar", headers=escenario["moderador"]).status_code == 403
    # Un egresado no entra al panel de la universidad.
    assert client.get("/api/encuestas", headers=escenario["sistemas_h"]).status_code == 403
    assert (
        client.post(
            "/api/encuestas", headers=escenario["sistemas_h"], json={"titulo": "No puede", "periodo": "X"}
        ).status_code
        == 403
    )
    # Ni el staff responde encuestas de egresados.
    assert client.get("/api/encuestas/mias", headers=escenario["admin"]).status_code == 403
    # Sin sesión, nada.
    assert client.get("/api/encuestas/mias").status_code in (401, 403)
