from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bitacora import BitacoraLog


class BitacoraRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def registrar(self, log: BitacoraLog) -> BitacoraLog:
        self.db.add(log)
        self.db.flush()
        return log

    def listar(
        self,
        usuario_id: int | None = None,
        modulo: str | None = None,
        accion: str | None = None,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
    ) -> list[BitacoraLog]:
        stmt = select(BitacoraLog).order_by(BitacoraLog.fecha.desc())
        if usuario_id is not None:
            stmt = stmt.where(BitacoraLog.usuario_id == usuario_id)
        if modulo is not None:
            stmt = stmt.where(BitacoraLog.modulo == modulo)
        if accion is not None:
            stmt = stmt.where(BitacoraLog.accion == accion)
        if fecha_desde is not None:
            stmt = stmt.where(BitacoraLog.fecha >= fecha_desde)
        if fecha_hasta is not None:
            stmt = stmt.where(BitacoraLog.fecha <= fecha_hasta)
        return list(self.db.scalars(stmt))
