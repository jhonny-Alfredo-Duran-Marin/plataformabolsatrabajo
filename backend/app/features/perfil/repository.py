import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.candidato import (
    CandidateCertification,
    CandidateEducation,
    CandidateExperience,
    CandidateLanguage,
    CandidateProfile,
    CandidateSkill,
)
from app.models.catalogo import Skill


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

    # --- Formación académica adicional ---
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

    # --- Experiencia laboral ---
    def listar_experiencia(self, candidate_id: uuid.UUID) -> list[CandidateExperience]:
        stmt = select(CandidateExperience).where(CandidateExperience.candidate_id == candidate_id)
        return list(self.db.scalars(stmt))

    def obtener_experiencia(self, item_id: uuid.UUID | str) -> CandidateExperience | None:
        return self.db.get(CandidateExperience, item_id)

    def crear_experiencia(self, item: CandidateExperience) -> CandidateExperience:
        self.db.add(item)
        self.db.flush()
        return item

    def eliminar_experiencia(self, item: CandidateExperience) -> None:
        self.db.delete(item)

    # --- Idiomas ---
    def listar_idiomas(self, candidate_id: uuid.UUID) -> list[CandidateLanguage]:
        stmt = select(CandidateLanguage).where(CandidateLanguage.candidate_id == candidate_id)
        return list(self.db.scalars(stmt))

    def obtener_idioma(self, item_id: uuid.UUID | str) -> CandidateLanguage | None:
        return self.db.get(CandidateLanguage, item_id)

    def crear_idioma(self, item: CandidateLanguage) -> CandidateLanguage:
        self.db.add(item)
        self.db.flush()
        return item

    def eliminar_idioma(self, item: CandidateLanguage) -> None:
        self.db.delete(item)

    # --- Certificaciones ---
    def listar_certificaciones(self, candidate_id: uuid.UUID) -> list[CandidateCertification]:
        stmt = select(CandidateCertification).where(CandidateCertification.candidate_id == candidate_id)
        return list(self.db.scalars(stmt))

    def obtener_certificacion(self, item_id: uuid.UUID | str) -> CandidateCertification | None:
        return self.db.get(CandidateCertification, item_id)

    def crear_certificacion(self, item: CandidateCertification) -> CandidateCertification:
        self.db.add(item)
        self.db.flush()
        return item

    def eliminar_certificacion(self, item: CandidateCertification) -> None:
        self.db.delete(item)

    # --- Habilidades (N:M con el catálogo) ---
    def listar_habilidades(self, candidate_id: uuid.UUID) -> list[Skill]:
        stmt = select(Skill).join(CandidateSkill, CandidateSkill.skill_id == Skill.id).where(
            CandidateSkill.candidate_id == candidate_id
        )
        return list(self.db.scalars(stmt))

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
