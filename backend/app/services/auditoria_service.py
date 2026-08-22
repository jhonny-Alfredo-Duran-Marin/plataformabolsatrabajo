from sqlalchemy.orm import Session

from app.models.auditoria import AuditoriaLog
from app.repositories.auditoria_repository import AuditoriaRepository


class AuditoriaService:
    def __init__(self, db: Session) -> None:
        self.repo = AuditoriaRepository(db)

    def registrar(
        self,
        modulo: str,
        accion: str,
        usuario_id: int | None = None,
        ip: str | None = None,
        detalles: str | None = None,
        resultado: bool = True,
    ) -> AuditoriaLog:
        log = AuditoriaLog(
            usuario_id=usuario_id, ip=ip, modulo=modulo, accion=accion, detalles=detalles, resultado=resultado
        )
        return self.repo.registrar(log)

    def listar(self, usuario_id: int | None = None, modulo: str | None = None, accion: str | None = None) -> list[AuditoriaLog]:
        return self.repo.listar(usuario_id=usuario_id, modulo=modulo, accion=accion)
