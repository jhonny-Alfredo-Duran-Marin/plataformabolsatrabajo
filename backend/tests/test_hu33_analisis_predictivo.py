"""HU-33: análisis predictivo — brecha de habilidades entre las vacantes y los egresados de una carrera."""
import time
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.features.ia.services import analisis_predictivo_service
from app.main import app
from app.models.candidato import CandidateEducation, CandidateProfile, CandidateSkill
from app.models.catalogo import FieldOfStudy, Skill
from app.models.empresa import Company
from app.models.institucion import CompanyInstitution, Institution
from app.models.usuario import AppUser, Role, UserRole
from app.models.vacante import JobEducationPreference, JobPosting, JobSkill
from app.security.jwt_provider import create_access_token
from app.shared import ia_generativa

client = TestClient(app)
URL = "/api/ia/analisis-predictivo/brecha-habilidades"


@pytest.fixture(autouse=True)
def sin_gemini(monkeypatch):
    """Ningún test de este archivo llama a Gemini de verdad, aunque el .env tenga la clave."""
    monkeypatch.setattr(get_settings(), "gemini_api_key_reportes", None)
    monkeypatch.setattr(get_settings(), "gemini_api_key_asistente", None)


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


def _cabecera(usuario: AppUser, rol: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token(str(usuario.id), rol, {'roles': [rol]})}"}


def _fecha(mes: int) -> datetime:
    return datetime(2026, mes, 10, 12, tzinfo=timezone.utc)


@pytest.fixture
def escenario(db_session: Session):
    """Una carrera con 6 vacantes y 6 egresados, cuya brecha se calcula a mano.

    Habilidades (6 vacantes, 6 egresados):
      Alfa: la piden 6 de 6 (100 %) y no la declara nadie (0 %)   -> brecha +100,0
      Delta: la pide 1 de 6 (16,7 %) y no la declara nadie        -> brecha  +16,7
      Beta: la piden 3 de 6 (50 %) y la declaran 3 de 6 (50 %)    -> brecha    0,0
      Gamma: la piden 2 de 6 (33,3 %) y la declaran 6 de 6 (100 %) -> brecha  -66,7
    Beta y Gamma se declaran con otras mayúsculas y espacios: cuentan como la misma habilidad.
    """
    db = db_session
    s = uuid.uuid4().hex[:6]
    uni = Institution(name=f"Universidad Brecha {s}", is_tenant=True, slug=f"br{s}")
    otra = Institution(name=f"Otra Universidad Brecha {s}", is_tenant=True, slug=f"ot{s}")
    db.add_all([uni, otra])
    db.flush()
    carrera = FieldOfStudy(name=f"Carrera Brecha {s}")
    db.add(carrera)
    empresa = Company(
        legal_name=f"Empresa Brecha {s}", tax_id=f"NIT-{uuid.uuid4().hex[:8]}",
        verification_status="verified", account_status="active",
    )
    ajena = Company(
        legal_name=f"Empresa No Habilitada {s}", tax_id=f"NIT-{uuid.uuid4().hex[:8]}",
        verification_status="verified", account_status="active",
    )
    db.add_all([empresa, ajena])
    db.flush()
    db.add(CompanyInstitution(company_id=empresa.id, institution_id=uni.id, status="approved"))
    # La otra universidad solo tiene 2 egresados de la carrera y ninguna empresa habilitada.

    habilidades = {n: Skill(name=f"{n} {s}", category="Técnica", is_active=True) for n in ("Alfa", "Beta", "Gamma", "Delta")}
    habilidades_egresado = {
        "Beta": Skill(name=f"BETA {s}", category="Técnica", is_active=True),
        "Gamma": Skill(name=f"gamma  {s}", category="Técnica", is_active=True),
    }
    db.add_all([*habilidades.values(), *habilidades_egresado.values()])
    db.flush()

    creador = _usuario(db, "empresa", "empresa")

    def vacante(titulo: str, nombres: list[str], estado="published", publicada=_fecha(3), empresa_id=empresa.id):
        v = JobPosting(
            company_id=empresa_id, title=f"{titulo} {s}", description="Vacante de prueba", seniority_level="junior",
            employment_type="permanent", work_modality="remote", city="Santa Cruz", status=estado,
            published_at=publicada, created_by=creador.id,
        )
        db.add(v)
        db.flush()
        db.add(JobEducationPreference(job_posting_id=v.id, field_of_study_id=carrera.id, is_required=False))
        for nombre in nombres:
            db.add(JobSkill(job_posting_id=v.id, skill_id=habilidades[nombre].id))
        db.flush()
        return v

    v6 = vacante("V6", ["Alfa", "Beta"], publicada=None)  # sin fecha de publicación: cuenta por su creación
    v6.created_at = _fecha(3)
    vacante("V1", ["Alfa", "Beta", "Gamma"])
    vacante("V2", ["Alfa", "Beta", "Gamma", "Delta"])
    vacante("V3", ["Alfa"])
    vacante("V4", ["Alfa"])
    vacante("V5", ["Alfa"], estado="archived")  # el histórico cuenta
    # Fuera del cálculo: sin habilidades, en borrador y de una empresa no habilitada en la universidad.
    vacante("Sin habilidades", [])
    vacante("Borrador", ["Delta"], estado="draft")
    vacante("Empresa ajena", ["Delta"], empresa_id=ajena.id)

    def egresado(universidad: uuid.UUID, nombres: list[str], validado=True) -> CandidateProfile:
        u = _usuario(db, "egresado", "candidate", universidad)
        p = CandidateProfile(
            user_id=u.id, first_name="Egresado", last_name="Brecha", institution_id=universidad,
            verification_status="verified" if validado else "pending",
        )
        db.add(p)
        db.flush()
        db.add(CandidateEducation(
            candidate_id=p.id, institution_id=universidad, field_of_study_id=carrera.id,
            program_name=carrera.name, academic_status="graduated",
        ))
        for nombre in nombres:
            origen = habilidades_egresado.get(nombre) or habilidades[nombre]
            db.add(CandidateSkill(candidate_id=p.id, skill_id=origen.id, proficiency_level="intermediate"))
        return p

    for declaradas in (["Beta", "Gamma"], ["Beta", "Gamma"], ["Beta", "Gamma"], ["Gamma"], ["Gamma"], ["Gamma"]):
        egresado(uni.id, declaradas)
    egresado(uni.id, ["Gamma"], validado=False)  # sin validar: no cuenta
    egresado(otra.id, ["Gamma"])
    egresado(otra.id, ["Gamma"])

    admin = _usuario(db, "admin", "platform_admin", uni.id)
    admin_otra = _usuario(db, "admin_otra", "platform_admin", otra.id)
    moderador = _usuario(db, "mod", "moderator", uni.id)
    empresa_user = _usuario(db, "empresa2", "empresa")
    db.commit()
    return {
        "s": s,
        "carrera": str(carrera.id),
        "admin": _cabecera(admin, "platform_admin"),
        "admin_otra": _cabecera(admin_otra, "platform_admin"),
        "moderador": _cabecera(moderador, "moderator"),
        "empresa": _cabecera(empresa_user, "empresa"),
    }


def _consultar(e: dict, quien: str = "admin", **params):
    return client.get(URL, headers=e[quien], params={"carrera_id": e["carrera"], **params})


# ─── CP01: datos suficientes -> lista ordenada ────────────────────────────


def test_cp01_datos_suficientes_lista_ordenada_de_mayor_a_menor_brecha(escenario):
    e = escenario
    res = _consultar(e)
    assert res.status_code == 200, res.text
    datos = res.json()

    assert datos["hay_suficientes_datos"] is True and datos["mensaje"] is None
    assert datos["carrera_id"] == e["carrera"] and datos["periodo"] is None
    # 6 vacantes con habilidades (la de borrador, la de empresa ajena y la sin habilidades no cuentan) y
    # 6 egresados validados de la carrera (el sin validar tampoco).
    assert datos["total_vacantes"] == 6 and datos["total_egresados"] == 6
    assert datos["vacantes_sin_habilidades"] == 1 and datos["egresados_sin_habilidades"] == 0

    filas = [(h["habilidad"], h["demanda_pct"], h["oferta_pct"], h["brecha"]) for h in datos["habilidades"]]
    esperado = [
        (f"Alfa {e['s']}", 100.0, 0.0, 100.0),
        (f"Delta {e['s']}", 16.7, 0.0, 16.7),
        (f"Beta {e['s']}", 50.0, 50.0, 0.0),
        (f"Gamma {e['s']}", 33.3, 100.0, -66.7),
    ]
    assert filas == esperado
    brechas = [h["brecha"] for h in datos["habilidades"]]
    assert brechas == sorted(brechas, reverse=True)
    assert datos["total_habilidades"] == 4
    assert datos["habilidades"][0]["demanda_vacantes"] == 6 and datos["habilidades"][0]["oferta_egresados"] == 0
    # Sin clave de Gemini el reporte sale igual, sin la lectura en texto.
    assert datos["resumen_ia"] is None

    # Filtro de período: las 6 vacantes son de marzo de 2026 (una por su fecha de creación).
    assert _consultar(e, periodo="2026").json()["total_vacantes"] == 6
    assert _consultar(e, periodo="2026-03").json()["total_vacantes"] == 6
    # El límite recorta la lista pero conserva el orden y el total.
    corto = _consultar(e, limite=2).json()
    assert [h["habilidad"] for h in corto["habilidades"]] == [f"Alfa {e['s']}", f"Delta {e['s']}"]
    assert corto["total_habilidades"] == 4


# ─── CP02: período sin datos -> mensaje ───────────────────────────────────


def test_cp02_periodo_sin_datos_devuelve_mensaje_de_datos_insuficientes(escenario):
    e = escenario
    res = _consultar(e, periodo="2026-04")  # nada se publicó en abril
    assert res.status_code == 200, res.text
    datos = res.json()
    assert datos["hay_suficientes_datos"] is False
    assert "no hay datos suficientes" in datos["mensaje"].lower()
    assert "2026-04" in datos["mensaje"] and "0 vacantes" in datos["mensaje"]
    assert datos["habilidades"] == [] and datos["total_habilidades"] == 0
    assert datos["total_vacantes"] == 0 and datos["total_egresados"] == 6
    assert datos["minimo_requerido"] == 5

    # También faltan datos si la universidad tiene pocos egresados de la carrera (la otra solo tiene 2).
    otra = _consultar(e, "admin_otra")
    assert otra.status_code == 200
    assert otra.json()["hay_suficientes_datos"] is False and otra.json()["total_egresados"] == 2

    # Validaciones: período mal escrito, carrera inexistente y carrera obligatoria.
    assert _consultar(e, periodo="2026-13").status_code == 422
    assert _consultar(e, periodo="marzo").status_code == 422
    assert client.get(URL, headers=e["admin"], params={"carrera_id": str(uuid.uuid4())}).status_code == 404
    assert client.get(URL, headers=e["admin"]).status_code == 422


# ─── CP03: usuario no administrador -> 403 ────────────────────────────────


def test_cp03_usuario_no_administrador_recibe_403(escenario):
    e = escenario
    assert _consultar(e, "moderador").status_code == 403
    assert _consultar(e, "empresa").status_code == 403
    assert client.get(URL, params={"carrera_id": e["carrera"]}).status_code == 401
    # Los selectores del reporte tienen la misma protección.
    assert client.get("/api/ia/analisis-predictivo/filtros", headers=e["moderador"]).status_code == 403
    assert client.get("/api/ia/analisis-predictivo/filtros", headers=e["empresa"]).status_code == 403
    # El administrador sí ve su carrera y sus períodos en los selectores.
    filtros = client.get("/api/ia/analisis-predictivo/filtros", headers=e["admin"])
    assert filtros.status_code == 200
    assert e["carrera"] in [c["id"] for c in filtros.json()["carreras"]]
    assert "2026-03" in filtros.json()["periodos"] and "2026" in filtros.json()["periodos"]


# ─── CP04: IA caída -> error controlado ───────────────────────────────────


def test_cp04_ia_caida_devuelve_los_datos_sin_resumen(escenario, monkeypatch):
    e = escenario
    sin_ia = _consultar(e).json()
    monkeypatch.setattr(get_settings(), "gemini_api_key_reportes", "clave-prueba")

    # Gemini responde con un error cualquiera: 200, resumen_ia null y los números intactos.
    def cae(*args, **kwargs):
        raise ia_generativa.IAGenerativaNoDisponible("Gemini no respondió.")

    monkeypatch.setattr(ia_generativa, "generar_json", cae)
    res = _consultar(e)
    assert res.status_code == 200, res.text
    assert res.json()["resumen_ia"] is None
    assert res.json()["habilidades"] == sin_ia["habilidades"]
    assert res.json()["hay_suficientes_datos"] is True

    # Un error inesperado tampoco tumba el reporte.
    monkeypatch.setattr(ia_generativa, "generar_json", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    assert _consultar(e).json()["resumen_ia"] is None

    # Si Gemini tarda más del máximo, la petición no espera: responde a tiempo y sin la lectura.
    monkeypatch.setattr(analisis_predictivo_service, "TIEMPO_MAXIMO_IA", 0.2)

    def lenta(*args, **kwargs):
        time.sleep(1.5)
        return {"resumen": "Texto tardío."}, "modelo-prueba"

    monkeypatch.setattr(ia_generativa, "generar_json", lenta)
    inicio = time.monotonic()
    res = _consultar(e)
    assert time.monotonic() - inicio < 1.2
    assert res.status_code == 200 and res.json()["resumen_ia"] is None
    assert res.json()["habilidades"] == sin_ia["habilidades"]

    # Con la IA funcionando, el texto se agrega y el resto no cambia.
    monkeypatch.setattr(analisis_predictivo_service, "TIEMPO_MAXIMO_IA", 5.0)
    monkeypatch.setattr(
        ia_generativa, "generar_json", lambda *a, **k: ({"resumen": "  Conviene reforzar   Alfa. "}, "modelo-prueba")
    )
    res = _consultar(e)
    assert res.status_code == 200
    assert res.json()["resumen_ia"] == "Conviene reforzar Alfa."
    assert res.json()["habilidades"] == sin_ia["habilidades"]
