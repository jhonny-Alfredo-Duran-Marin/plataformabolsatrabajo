from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.egresado import PerfilEgresado
from app.models.enums import EstadoValidacionEgresado


class EgresadoRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_por_usuario_id(self, usuario_id: int) -> PerfilEgresado | None:
        return self.db.scalar(select(PerfilEgresado).where(PerfilEgresado.usuario_id == usuario_id))

    def obtener_por_id(self, perfil_id: int) -> PerfilEgresado | None:
        return self.db.get(PerfilEgresado, perfil_id)

    def existe_ci(self, ci: str) -> bool:
        return self.db.scalar(select(PerfilEgresado).where(PerfilEgresado.ci == ci)) is not None

    def crear(self, perfil: PerfilEgresado) -> PerfilEgresado:
        self.db.add(perfil)
        self.db.flush()
        return perfil

    def listar_pendientes_validacion(self) -> list[PerfilEgresado]:
        stmt = select(PerfilEgresado).where(PerfilEgresado.estado_validacion == EstadoValidacionEgresado.PENDIENTE)
        return list(self.db.scalars(stmt))
