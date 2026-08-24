import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.candidato import CandidateProfile


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
