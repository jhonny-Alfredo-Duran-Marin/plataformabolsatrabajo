"""Motor de emparejamiento egresado↔vacante (módulo 5.1.11). Se implementa en Sprint 3."""

from sqlalchemy.orm import Session


class RecomendacionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def vacantes_recomendadas(self, perfil_egresado_id: int) -> list[dict]:
        raise NotImplementedError("Motor de recomendación pendiente de implementación (Sprint 3).")
