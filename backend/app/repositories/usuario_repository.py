from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.usuario import Usuario


class UsuarioRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_por_correo(self, correo: str) -> Usuario | None:
        return self.db.scalar(select(Usuario).where(Usuario.correo == correo))

    def obtener_por_id(self, usuario_id: int) -> Usuario | None:
        return self.db.get(Usuario, usuario_id)

    def crear(self, usuario: Usuario) -> Usuario:
        self.db.add(usuario)
        self.db.flush()
        return usuario

    def existe_correo(self, correo: str) -> bool:
        return self.obtener_por_correo(correo) is not None
