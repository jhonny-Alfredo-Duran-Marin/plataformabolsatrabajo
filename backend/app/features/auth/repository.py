import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.candidato import CandidateProfile
from app.models.empresa import Company, CompanyMember
from app.models.usuario import AppUser, Role, UserRole


class UsuarioRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_por_correo(self, correo: str) -> AppUser | None:
        stmt = select(AppUser).where(func.lower(AppUser.email) == correo.strip().lower(), AppUser.deleted_at.is_(None))
        return self.db.scalar(stmt)

    def obtener_por_id(self, usuario_id: uuid.UUID | str) -> AppUser | None:
        return self.db.get(AppUser, usuario_id)

    def crear(self, usuario: AppUser) -> AppUser:
        self.db.add(usuario)
        self.db.flush()
        return usuario

    def existe_correo(self, correo: str) -> bool:
        return self.obtener_por_correo(correo) is not None

    def asignar_rol(self, usuario: AppUser, nombre_rol: str) -> None:
        rol = self.db.scalar(select(Role).where(Role.name == nombre_rol))
        if rol is None:
            raise ValueError(f"El rol '{nombre_rol}' no existe en la base de datos.")
        ya_asignado = any(ur.role_id == rol.id for ur in usuario.user_roles)
        if not ya_asignado:
            self.db.add(UserRole(user_id=usuario.id, role_id=rol.id))
            self.db.flush()

    def pertenece_a_empresa(self, usuario_id: uuid.UUID) -> bool:
        stmt = select(CompanyMember.id).where(CompanyMember.user_id == usuario_id).limit(1)
        return self.db.scalar(stmt) is not None


class CandidateRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def existe_ci(self, ci: str) -> bool:
        stmt = select(CandidateProfile.id).where(
            CandidateProfile.document_type == "ci", CandidateProfile.document_number == ci
        )
        return self.db.scalar(stmt) is not None

    def crear(self, perfil: CandidateProfile) -> CandidateProfile:
        self.db.add(perfil)
        self.db.flush()
        return perfil


class EmpresaRegistroRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def existe_nit(self, nit: str) -> bool:
        return self.db.scalar(select(Company.id).where(Company.tax_id == nit)) is not None

    def crear(self, empresa: Company) -> Company:
        self.db.add(empresa)
        self.db.flush()
        return empresa

    def crear_miembro(self, miembro: CompanyMember) -> CompanyMember:
        self.db.add(miembro)
        self.db.flush()
        return miembro
