"""HU-36 — Notificaciones push ante cambios de estado de una postulación.

Casos de prueba cubiertos (docs/especificacion/hu/HU-36.md). Firebase va siempre simulado:
ningún test usa credenciales ni la red.

- CP01: token FCM activo -> la empresa avanza la postulación -> push con `tipo=application_status`.
- CP02: la empresa rechaza la postulación -> push con la vacante y el estado legible "No seleccionado".
- CP03: el egresado retira su postulación -> no se envía push.
- CP04: el push lleva la vacante en el título, el estado legible en el cuerpo, `postulacion_id` y enlace.
- CP09: `push_enabled = false` -> no hay push, pero sí aviso en la campanita y el estado se guarda.
- CP10: desactivar y volver a activar «Notificaciones push» -> el siguiente cambio vuelve a enviar push.
  (HU-21 solo prueba otras preferencias: test_hu21_notificaciones.py::test_cp03 y
  test_hu21_preferencias_reales.py::test_cada_preferencia_silencia_sus_tipos; este CP10 lo cubre acá.)
- CP11: Firebase falla (error pasajero) -> el estado se guarda y queda un push pendiente con `intentos = 1`.
- CP12: el reintento envía solo a los dispositivos que fallaron y queda como enviado, sin duplicar.
- CP13: el 3.er reintento también falla -> `fallido` con `intentos = 4` y no se vuelve a intentar.
- CP14: Firebase da un token por inválido -> se desactiva y no genera reintento.
"""

import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from firebase_admin import exceptions as fb_exceptions
from firebase_admin import messaging
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine
from app.core.esquema import asegurar_esquema_requisitos
from app.features.notificaciones import fcm_service
from app.features.notificaciones.reintento import reintentar_pendientes
from app.main import app
from app.models.candidato import CandidateProfile
from app.models.empresa import Company, CompanyMember
from app.models.notificacion import Notification, PushPending, UserDeviceToken
from app.models.postulacion import Application, ApplicationStatusHistory
from app.models.usuario import AppUser, Role, UserRole
from app.models.vacante import JobPosting, JobSelectionStage
from app.security.jwt_provider import create_access_token

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def tabla_push_pendiente():
    """La tabla push_pendiente la crea la migración HU-36; aquí se asegura en la BD local."""
    with engine.begin() as conn:
        asegurar_esquema_requisitos(conn)


@pytest.fixture
def db_session():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class FirebaseFalso:
    """Reemplaza `messaging.send_each_for_multicast`: cada token responde según `comportamiento`.

    Valores: "ok" (default), "pasajero" (error 503 de Firebase), "muerto" (token no registrado),
    "caido" (el envío completo lanza una excepción).
    """

    def __init__(self) -> None:
        self.comportamiento: dict[str, str] = {}
        self.por_defecto = "ok"
        self.enviados: list[SimpleNamespace] = []

    def __call__(self, mensaje):
        self.enviados.append(SimpleNamespace(tokens=list(mensaje.tokens), data=dict(mensaje.data), notification=mensaje.notification))
        respuestas = []
        for token in mensaje.tokens:
            modo = self.comportamiento.get(token, self.por_defecto)
            if modo == "caido":
                raise ConnectionError("Firebase no responde")
            if modo == "ok":
                respuestas.append(SimpleNamespace(success=True, exception=None))
            elif modo == "muerto":
                respuestas.append(
                    SimpleNamespace(
                        success=False, exception=messaging.UnregisteredError("token no registrado", None, None)
                    )
                )
            else:
                respuestas.append(
                    SimpleNamespace(success=False, exception=fb_exceptions.UnavailableError("Firebase no disponible"))
                )
        exitos = sum(r.success for r in respuestas)
        return SimpleNamespace(
            responses=respuestas, success_count=exitos, failure_count=len(respuestas) - exitos
        )

    def a(self, tokens: list[str]) -> list[SimpleNamespace]:
        """Envíos dirigidos a alguno de estos tokens (la BD local puede tener otros pendientes)."""
        return [e for e in self.enviados if set(e.tokens) & set(tokens)]


@pytest.fixture
def firebase(monkeypatch):
    falso = FirebaseFalso()
    monkeypatch.setattr(fcm_service, "inicializar_firebase", lambda: True)
    monkeypatch.setattr(messaging, "send_each_for_multicast", falso)
    return falso


def _usuario(db: Session, prefijo: str, rol: str) -> AppUser:
    if not db.query(Role).filter_by(name=rol).first():
        db.add(Role(name=rol))
        db.flush()
    usuario = AppUser(email=f"{prefijo}_{uuid.uuid4().hex[:8]}@test.bo", password_hash="x", account_status="active")
    db.add(usuario)
    db.flush()
    db.add(UserRole(user_id=usuario.id, role_id=db.query(Role).filter_by(name=rol).first().id))
    return usuario


def _auth(usuario: AppUser, rol: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token(str(usuario.id), rol, {'roles': [rol]})}"}


@pytest.fixture
def datos(db_session: Session):
    db = db_session
    sufijo = uuid.uuid4().hex[:6]
    reclutador = _usuario(db, "rrhh36", "empresa")
    empresa = Company(
        legal_name=f"Empresa HU36 {sufijo}",
        tax_id=f"NIT-{uuid.uuid4().hex[:8]}",
        verification_status="verified",
        account_status="active",
    )
    db.add(empresa)
    db.flush()
    db.add(CompanyMember(user_id=reclutador.id, company_id=empresa.id, member_type="recruiter", is_active=True))
    vacante = JobPosting(
        company_id=empresa.id,
        title=f"Analista Push {sufijo}",
        description="Vacante de prueba HU-36",
        seniority_level="junior",
        employment_type="permanent",
        work_modality="onsite",
        city="Santa Cruz",
        status="published",
        created_by=reclutador.id,
    )
    db.add(vacante)
    db.flush()
    etapa_revision = JobSelectionStage(job_posting_id=vacante.id, stage_number=1, name="Revisión de CV")
    etapa_entrevista = JobSelectionStage(job_posting_id=vacante.id, stage_number=2, name="Entrevista técnica")
    db.add_all([etapa_revision, etapa_entrevista])
    egresado = _usuario(db, "cand36", "candidate")
    perfil = CandidateProfile(user_id=egresado.id, first_name="Rosa", last_name="Prueba", verification_status="verified")
    db.add(perfil)
    db.flush()
    postulacion = Application(candidate_id=perfil.id, job_id=vacante.id, current_status="screening")
    db.add(postulacion)
    token_a = f"tok-a-{uuid.uuid4().hex}"
    token_b = f"tok-b-{uuid.uuid4().hex}"
    db.add_all(
        [
            UserDeviceToken(user_id=egresado.id, fcm_token=token_a, device_type="android", is_active=True),
            UserDeviceToken(user_id=egresado.id, fcm_token=token_b, device_type="android", is_active=True),
        ]
    )
    db.commit()
    return {
        "reclutador": reclutador,
        "egresado": egresado,
        "postulacion": postulacion,
        "vacante": vacante,
        "etapa_entrevista": etapa_entrevista,
        "tokens": [token_a, token_b],
        "token_a": token_a,
        "token_b": token_b,
    }


def _avanzar(datos: dict, etapa=None):
    etapa = etapa or datos["etapa_entrevista"]
    res = client.post(
        f"/api/seleccion/postulaciones/{datos['postulacion'].id}/avanzar",
        json={"stage_id": str(etapa.id)},
        headers=_auth(datos["reclutador"], "empresa"),
    )
    assert res.status_code == 200, res.text
    return res


def _descartar(datos: dict):
    res = client.post(
        f"/api/seleccion/postulaciones/{datos['postulacion'].id}/descartar",
        json={"motivo": "Perfil no ajustado"},
        headers=_auth(datos["reclutador"], "empresa"),
    )
    assert res.status_code == 200, res.text
    return res


def _avisos_estado(db: Session, egresado: AppUser) -> list[Notification]:
    db.expire_all()
    return db.query(Notification).filter_by(user_id=egresado.id, notification_type="application_status").all()


def _push_pendientes(db: Session, egresado: AppUser) -> list[PushPending]:
    db.expire_all()
    return db.query(PushPending).filter_by(user_id=egresado.id).all()


def test_cp01_avance_de_etapa_envia_push_a_los_tokens_activos(datos, firebase, db_session):
    """CP01: token FCM activo y preferencias por defecto -> la empresa avanza la etapa -> push con tipo=application_status."""
    _avanzar(datos)

    enviados = firebase.a(datos["tokens"])
    assert len(enviados) == 1
    assert set(enviados[0].tokens) == set(datos["tokens"])
    assert enviados[0].data["tipo"] == "application_status"
    assert _push_pendientes(db_session, datos["egresado"]) == []


def test_cp02_rechazo_envia_push_con_vacante_y_estado_legible(datos, firebase, db_session):
    """CP02: token activo -> la empresa rechaza -> push con el título de la vacante y "No seleccionado"."""
    _descartar(datos)

    enviados = firebase.a(datos["tokens"])
    assert len(enviados) == 1
    assert datos["vacante"].title in enviados[0].notification.title
    assert "No seleccionado" in enviados[0].notification.body
    assert enviados[0].data["tipo"] == "application_status"


def test_cp03_el_retiro_del_egresado_no_envia_push(datos, firebase, db_session):
    """CP03: el propio egresado retira su postulación -> no se envía push."""
    res = client.post(
        f"/api/postulaciones/{datos['postulacion'].id}/retirar",
        json={"motivo": "Ya conseguí trabajo"},
        headers=_auth(datos["egresado"], "candidate"),
    )
    assert res.status_code == 200, res.text

    assert firebase.a(datos["tokens"]) == []
    assert _avisos_estado(db_session, datos["egresado"]) == []


def test_cp04_contenido_del_push_vacante_estado_id_y_enlace(datos, firebase):
    """CP04: título con la vacante, cuerpo con el estado legible, data con postulacion_id y enlace /postulaciones?id=<id>."""
    _avanzar(datos)

    envio = firebase.a(datos["tokens"])[0]
    postulacion_id = str(datos["postulacion"].id)
    assert datos["vacante"].title in envio.notification.title
    assert "En entrevista" in envio.notification.body
    assert "interview" not in envio.notification.body  # estado legible, no el código
    assert envio.data["postulacion_id"] == postulacion_id
    assert envio.data["link"] == f"/postulaciones?id={postulacion_id}"
    assert envio.data["click_action"] == f"/postulaciones?id={postulacion_id}"
    # RNF-22: solo lo mínimo; nada de datos personales ni de notas internas.
    assert "Rosa" not in envio.notification.body and "Perfil no ajustado" not in envio.notification.body


def test_cp04_la_campanita_guarda_el_mismo_enlace(datos, firebase, db_session):
    """CP04 (campanita): el aviso queda con el enlace /postulaciones?id=<id> que la app usa para abrir el detalle."""
    _avanzar(datos)

    (aviso,) = _avisos_estado(db_session, datos["egresado"])
    assert aviso.link == f"/postulaciones?id={datos['postulacion'].id}"
    assert datos["vacante"].title in aviso.title


def test_cp09_push_desactivado_no_envia_pero_si_crea_el_aviso_y_guarda_el_estado(datos, firebase, db_session):
    """CP09: push_enabled = false -> no se envía push, el aviso sí se crea y el estado se guarda."""
    res = client.put(
        "/api/notificaciones/preferencias", json={"push_enabled": False}, headers=_auth(datos["egresado"], "candidate")
    )
    assert res.status_code == 200

    _descartar(datos)

    assert firebase.a(datos["tokens"]) == []
    assert len(_avisos_estado(db_session, datos["egresado"])) == 1
    db_session.expire_all()
    assert db_session.get(Application, datos["postulacion"].id).current_status == "rejected"


def test_cp10_desactivar_y_reactivar_push_en_preferencias(datos, firebase):
    """CP10: desactiva y vuelve a activar «Notificaciones push» -> GET devuelve lo guardado y el siguiente cambio vuelve a enviar push."""
    headers = _auth(datos["egresado"], "candidate")

    assert client.put("/api/notificaciones/preferencias", json={"push_enabled": False}, headers=headers).status_code == 200
    assert client.get("/api/notificaciones/preferencias", headers=headers).json()["push_enabled"] is False

    assert client.put("/api/notificaciones/preferencias", json={"push_enabled": True}, headers=headers).status_code == 200
    assert client.get("/api/notificaciones/preferencias", headers=headers).json()["push_enabled"] is True

    _avanzar(datos)
    assert len(firebase.a(datos["tokens"])) == 1


def test_cp11_error_pasajero_guarda_el_estado_y_deja_el_push_pendiente(datos, firebase, db_session):
    """CP11: Firebase responde con error pasajero -> el estado y el historial se guardan y queda un push pendiente con intentos = 1."""
    firebase.por_defecto = "pasajero"

    _avanzar(datos)

    db_session.expire_all()
    postulacion = db_session.get(Application, datos["postulacion"].id)
    assert postulacion.current_status == "interview"
    historial = db_session.query(ApplicationStatusHistory).filter_by(application_id=postulacion.id).all()
    assert [h.to_status for h in historial] == ["interview"]

    (pendiente,) = _push_pendientes(db_session, datos["egresado"])
    assert pendiente.estado == "pendiente"
    assert pendiente.intentos == 1
    assert set(pendiente.tokens) == set(datos["tokens"])
    assert pendiente.datos["postulacion_id"] == str(postulacion.id)
    assert pendiente.enlace == f"/postulaciones?id={postulacion.id}"


def test_cp11_si_firebase_no_responde_tambien_queda_pendiente(datos, firebase, db_session):
    """CP11 (variante): el envío completo lanza una excepción de red -> el estado se guarda y el push queda pendiente."""
    firebase.por_defecto = "caido"

    _avanzar(datos)

    db_session.expire_all()
    assert db_session.get(Application, datos["postulacion"].id).current_status == "interview"
    (pendiente,) = _push_pendientes(db_session, datos["egresado"])
    assert pendiente.intentos == 1
    assert "Firebase no responde" in (pendiente.ultimo_error or "")


def test_cp12_el_reintento_envia_solo_a_los_que_fallaron_sin_duplicar(datos, firebase, db_session):
    """CP12: push pendiente y Firebase disponible -> el reintento lo envía, queda enviado y no se duplica en los que ya lo recibieron."""
    firebase.comportamiento = {datos["token_b"]: "pasajero"}  # el dispositivo A lo recibe, el B no
    _avanzar(datos)
    (pendiente,) = _push_pendientes(db_session, datos["egresado"])
    assert pendiente.tokens == [datos["token_b"]]
    firebase.enviados.clear()
    firebase.comportamiento = {}  # Firebase ya responde bien

    with SessionLocal() as db:
        reintentar_pendientes(db)

    envios = firebase.a(datos["tokens"])
    assert len(envios) == 1
    assert envios[0].tokens == [datos["token_b"]]  # el dispositivo A no recibe el aviso dos veces
    assert envios[0].data["postulacion_id"] == str(datos["postulacion"].id)
    (pendiente,) = _push_pendientes(db_session, datos["egresado"])
    assert pendiente.estado == "enviado"
    assert pendiente.intentos == 2

    firebase.enviados.clear()
    with SessionLocal() as db:
        reintentar_pendientes(db)
    assert firebase.a(datos["tokens"]) == []  # un enviado no se vuelve a revisar


def test_cp13_el_tercer_reintento_fallido_deja_el_push_como_fallido_definitivo(datos, firebase, db_session):
    """CP13: ya falló el envío original y dos reintentos -> el 3.er reintento falla -> fallido con intentos = 4, sin más intentos."""
    firebase.por_defecto = "pasajero"
    _avanzar(datos)

    for esperado in (2, 3, 4):
        with SessionLocal() as db:
            reintentar_pendientes(db)
        (pendiente,) = _push_pendientes(db_session, datos["egresado"])
        assert pendiente.intentos == esperado
        assert pendiente.estado == ("pendiente" if esperado < 4 else "fallido")

    firebase.enviados.clear()
    with SessionLocal() as db:
        reintentar_pendientes(db)
    assert firebase.a(datos["tokens"]) == []
    (pendiente,) = _push_pendientes(db_session, datos["egresado"])
    assert pendiente.estado == "fallido"
    assert pendiente.intentos == 4


def test_cp14_token_invalido_se_desactiva_y_no_se_reintenta(datos, firebase, db_session):
    """CP14: Firebase responde que un token es inválido -> se envía el push -> ese token se desactiva y no genera reintento."""
    firebase.comportamiento = {datos["token_b"]: "muerto"}

    _avanzar(datos)

    db_session.expire_all()
    activos = {t.fcm_token: t.is_active for t in db_session.query(UserDeviceToken).filter_by(user_id=datos["egresado"].id)}
    assert activos[datos["token_b"]] is False
    assert activos[datos["token_a"]] is True
    assert _push_pendientes(db_session, datos["egresado"]) == []


def test_cp14_mezcla_de_token_muerto_y_error_pasajero_solo_reintenta_el_pasajero(datos, firebase, db_session):
    """CP14 (mezcla): un token muerto y otro con error pasajero -> el muerto se desactiva y solo el otro queda pendiente."""
    firebase.comportamiento = {datos["token_a"]: "pasajero", datos["token_b"]: "muerto"}

    _avanzar(datos)

    (pendiente,) = _push_pendientes(db_session, datos["egresado"])
    assert pendiente.tokens == [datos["token_a"]]
    db_session.expire_all()
    assert db_session.query(UserDeviceToken).filter_by(fcm_token=datos["token_b"]).one().is_active is False
