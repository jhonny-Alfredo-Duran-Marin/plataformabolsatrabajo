"""Cuenta de prueba del egresado Antonio (antonio@prueba.com) con su perfil completo.

Las pruebas de la HU-26 (tests/test_hu26_asistente_generativo.py) entran con este egresado por su
UUID fijo (90000000-0000-0000-0000-000000000003). La cuenta existe en la base compartida, pero una
base local nueva no la tiene: sin ella esas pruebas responden «Perfil de egresado no encontrado».

Crea, en la UAGRM:

- el usuario y su perfil de egresado validado;
- la carrera principal (Ingeniería de Sistemas, egresado en 2023);
- 2 experiencias laborales (una pasantía y su cargo actual);
- 7 habilidades (5 técnicas y 2 blandas) y 2 idiomas.

Es idempotente: si el usuario, el perfil o cualquiera de esas filas ya existe no la toca, así que
volver a correrlo no cambia nada. Si el correo o el UUID ya pertenecen a otra cuenta no hace nada y
lo avisa: nunca cambia la contraseña de un usuario que no sembró. La cuenta usa la contraseña
DEMO_PASSWORD de backend/.env.

Los catálogos (carrera, habilidades, idiomas) se buscan por nombre y, si falta alguno, se agrega.
Conviene correrlo antes de sembrar_escenario_demo: ahí Antonio recibe una entrevista y una
postulación a «Analista Funcional».

Uso (desde la carpeta backend):
    python -m scripts.sembrar_antonio_prueba
"""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select

import app.models  # noqa: F401 - registra todos los modelos
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.tenancy import INSTITUCION_POR_DEFECTO_ID as UAGRM
from app.features.perfil.repository import EgresadoRepository
from app.models.candidato import CandidateEducation, CandidateLanguage, CandidateProfile, CandidateSkill, WorkExperience
from app.models.catalogo import FieldOfStudy, Language, Skill
from app.models.institucion import Institution
from app.models.usuario import AppUser, Role, UserRole
from app.security.password_hasher import hash_password

ANTONIO_ID = uuid.UUID("90000000-0000-0000-0000-000000000003")
CORREO = "antonio@prueba.com"
CARRERA = "Ingeniería de Sistemas"
ANIO_EGRESO = 2023
# (nombre del catálogo, categoría si hay que crearla, nivel)
HABILIDADES = (
    ("Python", "Técnica", "advanced"),
    ("SQL", "Técnica", "advanced"),
    ("Git & GitHub", "Técnica", "intermediate"),
    ("Angular", "Técnica", "intermediate"),
    ("TypeScript", "Técnica", "intermediate"),
    ("Trabajo en Equipo", "Blanda", "advanced"),
    ("Comunicacion Asertiva", "Blanda", "intermediate"),
)
# (nombre, código ISO, nivel)
IDIOMAS = (("Español", "es", "native"), ("Inglés", "en", "intermediate"))
# (cargo, empresa, tipo, inicio, fin o None si es el actual, descripción)
EXPERIENCIAS = (
    ("Pasante de Desarrollo", "Pampa Software", "internship", date(2023, 6, 1), date(2023, 12, 15),
     "Mantenimiento de servicios REST y consultas SQL del sistema de gestión de la empresa."),
    ("Desarrollador Backend Junior", "Andes Digital", "full_time", date(2024, 3, 1), None,
     "Desarrollo de APIs en Python y paneles en Angular para clientes de banca y retail."),
)


def _usuario(db) -> AppUser | None:
    """El usuario de Antonio; None si el correo o el UUID ya son de otra cuenta."""
    por_id = db.get(AppUser, ANTONIO_ID)
    por_correo = db.scalar(select(AppUser).where(AppUser.email == CORREO))
    if por_id is not None and por_id.email != CORREO:
        print(f"  - Se saltea: el UUID {ANTONIO_ID} ya es de {por_id.email}.")
        return None
    if por_correo is not None and por_correo.id != ANTONIO_ID:
        print(f"  - Se saltea: {CORREO} ya existe con otro UUID ({por_correo.id}) y las pruebas de la HU-26 usan {ANTONIO_ID}.")
        return None
    if por_id is not None:
        print("  Usuario: ya estaba.")
        return por_id

    usuario = AppUser(
        id=ANTONIO_ID,
        email=CORREO,
        password_hash=hash_password(get_settings().demo_password),
        account_status="active",
    )
    db.add(usuario)
    db.flush()
    rol = db.scalar(select(Role).where(Role.name == "candidate"))
    if rol is None:
        rol = Role(name="candidate")
        db.add(rol)
        db.flush()
    db.add(UserRole(user_id=usuario.id, role_id=rol.id))
    print("  Usuario: creado.")
    return usuario


def _perfil(db, usuario: AppUser) -> tuple[CandidateProfile, bool]:
    perfil = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == usuario.id))
    if perfil is not None:
        return perfil, False
    perfil = CandidateProfile(
        user_id=usuario.id,
        institution_id=UAGRM,
        first_name="Antonio",
        last_name="Prueba",
        phone="+591 70000003",
        country_code="BO",
        city="Santa Cruz de la Sierra",
        professional_headline="Ingeniero de Sistemas",
        professional_summary="Ingeniero de Sistemas egresado de la UAGRM, interesado en desarrollo backend y análisis de datos.",
        document_type="ci",
        document_number="9900003",
        document_country_code="BO",
        verification_status="verified",
        verified_at=datetime.now(timezone.utc),
        availability="inmediata",
        job_search_status="actively_looking",
        profile_visibility="platform",
        contact_visibility=True,
    )
    db.add(perfil)
    db.flush()
    return perfil, True


def _carrera(db) -> FieldOfStudy:
    carrera = db.scalar(select(FieldOfStudy).where(FieldOfStudy.name == CARRERA))
    if carrera is None:
        carrera = FieldOfStudy(name=CARRERA, category="Ingeniería")
        db.add(carrera)
        db.flush()
    return carrera


def _formacion(db, perfil: CandidateProfile) -> int:
    marcador = EgresadoRepository.MARCADOR_EDUCACION_REGISTRO
    ya = db.scalar(
        select(CandidateEducation.id).where(
            CandidateEducation.candidate_id == perfil.id, CandidateEducation.description.like(f"{marcador}%")
        )
    )
    if ya is not None:
        return 0
    universidad = db.get(Institution, UAGRM)
    db.add(
        CandidateEducation(
            candidate_id=perfil.id,
            institution_id=UAGRM,
            institution_name=universidad.name if universidad else None,
            field_of_study_id=_carrera(db).id,
            program_name="Carrera universitaria",
            education_level="undergraduate",
            academic_status="graduated",
            graduation_date=date(ANIO_EGRESO, 12, 15),
            description=f"{marcador} Matrícula: 2019{ANIO_EGRESO}9003",
        )
    )
    return 1


def _experiencias(db, perfil: CandidateProfile) -> int:
    nuevas = 0
    for cargo, empresa, tipo, inicio, fin, descripcion in EXPERIENCIAS:
        ya = db.scalar(
            select(WorkExperience.id).where(
                WorkExperience.candidate_id == perfil.id,
                WorkExperience.position_title == cargo,
                WorkExperience.company_name == empresa,
            )
        )
        if ya is not None:
            continue
        db.add(
            WorkExperience(
                candidate_id=perfil.id,
                company_name=empresa,
                position_title=cargo,
                employment_type=tipo,
                start_date=inicio,
                end_date=fin,
                currently_working=fin is None,
                description=descripcion,
                location="Santa Cruz de la Sierra",
            )
        )
        nuevas += 1
    return nuevas


def _habilidades(db, perfil: CandidateProfile) -> int:
    propias = {s.skill_id for s in db.scalars(select(CandidateSkill).where(CandidateSkill.candidate_id == perfil.id))}
    nuevas = 0
    for nombre, categoria, nivel in HABILIDADES:
        habilidad = db.scalar(select(Skill).where(Skill.name == nombre))
        if habilidad is None:
            habilidad = Skill(name=nombre, category=categoria, is_active=True)
            db.add(habilidad)
            db.flush()
        if habilidad.id in propias:
            continue
        db.add(CandidateSkill(candidate_id=perfil.id, skill_id=habilidad.id, proficiency_level=nivel))
        nuevas += 1
    return nuevas


def _idiomas(db, perfil: CandidateProfile) -> int:
    propios = {i.language_id for i in db.scalars(select(CandidateLanguage).where(CandidateLanguage.candidate_id == perfil.id))}
    nuevos = 0
    for nombre, iso, nivel in IDIOMAS:
        idioma = db.scalar(select(Language).where((Language.name == nombre) | (Language.iso_code == iso)))
        if idioma is None:
            idioma = Language(name=nombre, iso_code=iso)
            db.add(idioma)
            db.flush()
        if idioma.id in propios:
            continue
        db.add(CandidateLanguage(candidate_id=perfil.id, language_id=idioma.id, proficiency_level=nivel))
        nuevos += 1
    return nuevos


def ejecutar() -> None:
    with SessionLocal() as db:
        if db.get(Institution, UAGRM) is None:
            print("Falta la UAGRM: corré antes python -m scripts.migrar_multitenant")
            return
        print(f"== {CORREO} ==")
        usuario = _usuario(db)
        if usuario is None:
            return
        perfil, creado = _perfil(db, usuario)
        print(f"  Perfil: {'creado' if creado else 'ya estaba'}.")
        formacion = _formacion(db, perfil)
        experiencias = _experiencias(db, perfil)
        habilidades = _habilidades(db, perfil)
        idiomas = _idiomas(db, perfil)
        db.commit()
        print(
            f"  Agregado: {formacion} formación, {experiencias} experiencias, {habilidades} habilidades "
            f"y {idiomas} idiomas."
        )

    print("\nListo. La cuenta usa la contraseña de DEMO_PASSWORD.")


if __name__ == "__main__":
    ejecutar()
