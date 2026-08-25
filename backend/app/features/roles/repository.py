import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.empresa import CompanyMember
from app.models.usuario import AppUser, Role, UserRole


class RolesRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def listar_usuarios(self) -> list[AppUser]:
        stmt = (
            select(AppUser)
            .where(AppUser.deleted_at.is_(None))
            .order_by(AppUser.created_at.desc())
        )
        return list(self.db.scalars(stmt))

    def obtener_usuario(self, usuario_id: uuid.UUID | str) -> AppUser | None:
        return self.db.scalar(
            select(AppUser).where(AppUser.id == usuario_id, AppUser.deleted_at.is_(None))
        )

    def listar_roles(self) -> list[Role]:
        return list(self.db.scalars(select(Role).order_by(Role.name)))

    def obtener_rol_por_nombre(self, nombre: str) -> Role | None:
        return self.db.scalar(select(Role).where(Role.name == nombre))

    def roles_de_usuario(self, usuario_id: uuid.UUID) -> list[str]:
        stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == usuario_id)
        return [r for (r,) in self.db.execute(stmt).all()]

    def reemplazar_roles(self, usuario_id: uuid.UUID, rol: Role) -> None:
        """Deja al usuario con exactamente un rol (regla: sin rol no puede existir)."""
        self.db.query(UserRole).filter(UserRole.user_id == usuario_id).delete()
        self.db.add(UserRole(user_id=usuario_id, role_id=rol.id))
        self.db.flush()

    def es_miembro_empresa(self, usuario_id: uuid.UUID) -> bool:
        return self.db.scalar(select(func.count()).select_from(CompanyMember).where(CompanyMember.user_id == usuario_id)) > 0
