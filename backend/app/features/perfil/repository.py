import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.candidato import (
    CandidateEducation,
    CandidateLanguage,
    CandidateProfile,
    CandidateSkill,
    Certification,
    WorkExperience,
)
from app.models.catalogo import Language, Skill


class EgresadoRepository:
    """Acceso a candidate_profile (perfil del egresado/candidato)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_por_usuario_id(self, usuario_id: uuid.UUID | str) -> CandidateProfile | None:
        return self.db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == usuario_id))

    def obtener_por_id(self, perfil_id: uuid.UUID | str) -> CandidateProfile | None:
        return self.db.get(CandidateProfile, perfil_id)

    def crear(self, perfil: CandidateProfile) -> CandidateProfile:
        self.db.add(perfil)
        self.db.flush()
        return perfil

    def listar_pendientes_validacion(self) -> list[CandidateProfile]:
        stmt = select(CandidateProfile).where(
            CandidateProfile.verification_status.in_(["pending", "in_review"]),
            CandidateProfile.document_number.is_not(None),
        )
        return list(self.db.scalars(stmt))

    # --- Formación académica ---
    def listar_formacion(self, candidate_id: uuid.UUID) -> list[CandidateEducation]:
        stmt = select(CandidateEducation).where(CandidateEducation.candidate_id == candidate_id)
        return list(self.db.scalars(stmt))

    def obtener_formacion(self, item_id: uuid.UUID | str) -> CandidateEducation | None:
        return self.db.get(CandidateEducation, item_id)

    def crear_formacion(self, item: CandidateEducation) -> CandidateEducation:
        self.db.add(item)
        self.db.flush()
        return item

    def eliminar_formacion(self, item: CandidateEducation) -> None:
        self.db.delete(item)

    MARCADOR_EDUCACION_REGISTRO = "[registro-carrera]"

    def obtener_educacion_principal(self, candidate_id: uuid.UUID) -> CandidateEducation | None:
        """Fila de candidate_education que representa la carrera/año/matrícula capturados
        en el registro. Se identifica con un marcador fijo en `description` (candidate_education
        no tiene columna para matrícula ni una bandera "es del registro"), ya que las filas que
        el usuario agrega manualmente desde "Formación adicional" no llevan ese marcador."""
        stmt = (
            select(CandidateEducation)
            .where(
                CandidateEducation.candidate_id == candidate_id,
                CandidateEducation.description.like(f"{self.MARCADOR_EDUCACION_REGISTRO}%"),
            )
            .order_by(CandidateEducation.created_at.asc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def educacion_principal_de(self, candidate_ids: list[uuid.UUID]) -> dict[uuid.UUID, CandidateEducation]:
        """Versión batch de obtener_educacion_principal: una sola query para
        todos los candidatos en vez de una por candidato (evita N+1 al listar)."""
        if not candidate_ids:
            return {}
        stmt = (
            select(CandidateEducation)
            .where(
                CandidateEducation.candidate_id.in_(candidate_ids),
                CandidateEducation.description.like(f"{self.MARCADOR_EDUCACION_REGISTRO}%"),
            )
            .order_by(CandidateEducation.candidate_id, CandidateEducation.created_at.asc())
        )
        resultado: dict[uuid.UUID, CandidateEducation] = {}
        for fila in self.db.scalars(stmt):
            resultado.setdefault(fila.candidate_id, fila)
        return resultado

    # --- Experiencia laboral (tabla work_experience) ---
    def listar_experiencia(self, candidate_id: uuid.UUID) -> list[WorkExperience]:
        stmt = select(WorkExperience).where(WorkExperience.candidate_id == candidate_id)
        return list(self.db.scalars(stmt))

    def obtener_experiencia(self, item_id: uuid.UUID | str) -> WorkExperience | None:
        return self.db.get(WorkExperience, item_id)

    def crear_experiencia(self, item: WorkExperience) -> WorkExperience:
        self.db.add(item)
        self.db.flush()
        return item

    def eliminar_experiencia(self, item: WorkExperience) -> None:
        self.db.delete(item)

    # --- Idiomas (candidate_language contra el catálogo language) ---
    def listar_idiomas(self, candidate_id: uuid.UUID) -> list[tuple[CandidateLanguage, Language]]:
        stmt = (
            select(CandidateLanguage, Language)
            .join(Language, Language.id == CandidateLanguage.language_id)
            .where(CandidateLanguage.candidate_id == candidate_id)
        )
        return [(cl, lang) for cl, lang in self.db.execute(stmt).all()]

    def obtener_idioma(self, candidate_id: uuid.UUID, language_id: uuid.UUID | str) -> CandidateLanguage | None:
        return self.db.get(CandidateLanguage, {"candidate_id": candidate_id, "language_id": language_id})

    def crear_idioma(self, item: CandidateLanguage) -> CandidateLanguage:
        self.db.add(item)
        self.db.flush()
        return item

    def eliminar_idioma(self, item: CandidateLanguage) -> None:
        self.db.delete(item)

    def obtener_o_crear_idioma(self, nombre: str) -> Language:
        idioma = self.db.scalar(select(Language).where(Language.name == nombre))
        if idioma is None:
            idioma = Language(name=nombre)
            self.db.add(idioma)
            self.db.flush()
        return idioma

    # --- Certificaciones ---
    def listar_certificaciones(self, candidate_id: uuid.UUID) -> list[Certification]:
        stmt = select(Certification).where(Certification.candidate_id == candidate_id)
        return list(self.db.scalars(stmt))

    def obtener_certificacion(self, item_id: uuid.UUID | str) -> Certification | None:
        return self.db.get(Certification, item_id)

    def crear_certificacion(self, item: Certification) -> Certification:
        self.db.add(item)
        self.db.flush()
        return item

    def eliminar_certificacion(self, item: Certification) -> None:
        self.db.delete(item)

    # --- Habilidades (N:M con el catálogo) ---
    def listar_habilidades(self, candidate_id: uuid.UUID) -> list[Skill]:
        stmt = select(Skill).join(CandidateSkill, CandidateSkill.skill_id == Skill.id).where(
            CandidateSkill.candidate_id == candidate_id
        )
        return list(self.db.scalars(stmt))

    def cantidad_habilidades_de(self, candidate_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
        """Versión batch de len(listar_habilidades(...)): una sola query para
        todos los candidatos en vez de una por candidato (evita N+1 al listar)."""
        if not candidate_ids:
            return {}
        stmt = (
            select(CandidateSkill.candidate_id, func.count())
            .where(CandidateSkill.candidate_id.in_(candidate_ids))
            .group_by(CandidateSkill.candidate_id)
        )
        return dict(self.db.execute(stmt).all())

    def reemplazar_habilidades(self, candidate_id: uuid.UUID, skill_ids: list[uuid.UUID]) -> None:
        self.db.query(CandidateSkill).filter(CandidateSkill.candidate_id == candidate_id).delete()
        for skill_id in skill_ids:
            self.db.add(CandidateSkill(candidate_id=candidate_id, skill_id=skill_id))
        self.db.flush()

    def obtener_o_crear_habilidad(self, nombre: str) -> Skill:
        skill = self.db.scalar(select(Skill).where(Skill.name == nombre))
        if skill is None:
            skill = Skill(name=nombre)
            self.db.add(skill)
            self.db.flush()
        return skill
