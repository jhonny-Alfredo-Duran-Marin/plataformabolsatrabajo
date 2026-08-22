"""Estimación de empleabilidad y brecha de habilidades (módulo 5.1.14). Se implementa en Sprint 4."""

from sqlalchemy.orm import Session


class AnalisisPredictivoService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def brecha_habilidades_por_carrera(self, carrera_id: int) -> dict:
        raise NotImplementedError("Análisis predictivo pendiente de implementación (Sprint 4).")
