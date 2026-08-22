from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auditoria import AuditoriaLog


class AuditoriaRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def registrar(self, log: AuditoriaLog) -> AuditoriaLog:
        self.db.add(log)
        self.db.flush()
        return log

    def listar(
        self,
        usuario_id: int | None = None,
        modulo: str | None = None,
        accion: str | None = None,
    ) -> list[AuditoriaLog]:
        stmt = select(AuditoriaLog).order_by(AuditoriaLog.fecha.desc())
        if usuario_id is not None:
            stmt = stmt.where(AuditoriaLog.usuario_id == usuario_id)
        if modulo is not None:
            stmt = stmt.where(AuditoriaLog.modulo == modulo)
        if accion is not None:
            stmt = stmt.where(AuditoriaLog.accion == accion)
        return list(self.db.scalars(stmt))
