from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.common.exceptions import ConflictException, UnauthorizedException
from app.features.auth.repository import (
    CandidateRepository,
    EmpresaRegistroRepository,
    UsuarioRepository,
)
from app.features.auth.schema import RegistroEgresadoRequest, RegistroEmpresaRequest, TokenResponse
from app.models.candidato import CandidateProfile
from app.models.empresa import Company, CompanyMember, Sector
from app.models.seguridad import LoginAttempt
from app.models.usuario import AppUser
from app.security.jwt_provider import create_access_token, create_refresh_token
from app.security.login_rate_limiter import limpiar_intentos, registrar_intento_fallido, verificar_bloqueo
from app.security.password_hasher import hash_password, verify_password
from app.shared.email_service import EmailService

_ROL_PRIORIDAD = ("platform_admin", "moderator", "empresa", "candidate")


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.usuarios = UsuarioRepository(db)
        self.candidatos = CandidateRepository(db)
        self.empresas = EmpresaRegistroRepository(db)
        self.email_service = EmailService()

    def registrar_egresado(self, data: RegistroEgresadoRequest) -> AppUser:
        if self.usuarios.existe_correo(data.correo):
            raise ConflictException("El correo electrónico ya está registrado.")
        if self.candidatos.existe_ci(data.ci):
            raise ConflictException("Ya existe un egresado registrado con ese CI.")
        if data.carrera_id is not None and self.db.get(Sector, data.carrera_id) is None:
            # Nota: el formulario envía field_of_study; se valida contra sector por compatibilidad histórica.
            from app.models.catalogo import FieldOfStudy

            if self.db.get(FieldOfStudy, data.carrera_id) is None:
                raise ConflictException("La carrera indicada no existe.")

        usuario = AppUser(email=data.correo.strip().lower(), password_hash=hash_password(data.password))
        self.usuarios.crear(usuario)
        self.usuarios.asignar_rol(usuario, "candidate")
        self.candidatos.crear(
            CandidateProfile(
                user_id=usuario.id,
                first_name=data.nombres.strip(),
                last_name=data.apellidos.strip(),
                country_code="BO",
                document_type="ci",
                document_number=data.ci,
                document_country_code="BO",
                verification_status="pending",
            )
        )
        self.db.commit()
        self.email_service.enviar(
            data.correo, "Verifica tu cuenta en EGRESA", "Gracias por registrarte. Confirma tu cuenta para continuar."
        )
        return usuario

    def registrar_empresa(self, data: RegistroEmpresaRequest) -> AppUser:
        if self.usuarios.existe_correo(data.correo):
            raise ConflictException("El correo electrónico ya está registrado.")
        if self.empresas.existe_nit(data.nit):
            raise ConflictException("Ya existe una empresa registrada con ese NIT/RUC.")

        sector_id = None
        if data.sector:
            sector = self.db.scalar(select(Sector).where(func.lower(Sector.name) == data.sector.lower()))
            sector_id = sector.id if sector else None

        usuario = AppUser(email=data.correo.strip().lower(), password_hash=hash_password(data.password))
        self.usuarios.crear(usuario)

        empresa = Company(
            legal_name=data.razon_social,
            tax_id=data.nit,
            sector_id=sector_id,
            company_size=data.tamanio,
            description=data.descripcion,
            website=data.sitio_web,
            phone=data.telefono,
            contact_email=data.correo.strip().lower(),
            country_code="BO",
            city=data.ciudad,
            address=data.direccion,
            legal_representative=data.representante_legal,
            verification_status="pending",
            account_status="active",
        )
        self.empresas.crear(empresa)
        self.empresas.crear_miembro(
            CompanyMember(user_id=usuario.id, company_id=empresa.id, member_type="owner", job_title="Propietario")
        )

        self.db.commit()
        self.email_service.enviar(
            data.correo,
            "Solicitud de registro recibida",
            "Tu empresa fue registrada y está pendiente de autorización por la UAGRM.",
        )
        return usuario

    def login(self, correo: str, password: str) -> tuple[TokenResponse, AppUser]:
        verificar_bloqueo(correo)
        usuario = self.usuarios.obtener_por_correo(correo)

        if usuario is None or not verify_password(password, usuario.password_hash):
            registrar_intento_fallido(correo)
            self._registrar_login_attempt(correo, usuario, success=False)
            raise UnauthorizedException("Correo o contraseña incorrectos.")

        if not usuario.activo:
            estado = (
                "pendiente de verificación" if usuario.account_status == "pending_verification" else "desactivada"
            )
            raise UnauthorizedException(f"La cuenta se encuentra {estado}.")

        limpiar_intentos(correo)
        usuario.last_login_at = func.now()
        roles = usuario.nombres_roles or (
            ["empresa"] if self.usuarios.pertenece_a_empresa(usuario.id) else ["candidate"]
        )
        rol_principal = next((r for r in _ROL_PRIORIDAD if r in roles), roles[0] if roles else "candidate")

        self._registrar_login_attempt(correo, usuario, success=True)

        subject = str(usuario.id)
        token = TokenResponse(
            access_token=create_access_token(subject, rol_principal, {"roles": roles}),
            refresh_token=create_refresh_token(subject, rol_principal),
            rol=rol_principal,
            roles=roles,
        )
        return token, usuario

    def _registrar_login_attempt(self, correo: str, usuario: AppUser | None, success: bool) -> None:
        self.db.add(
            LoginAttempt(email=correo.strip().lower(), user_id=usuario.id if usuario else None, success=success)
        )
