from sqlalchemy.orm import Session

from app.common.exceptions import ConflictException, UnauthorizedException
from app.models.egresado import PerfilEgresado
from app.models.empresa import Empresa
from app.models.enums import EstadoVerificacionEmpresa, RolNombre
from app.models.usuario import Usuario
from app.repositories.egresado_repository import EgresadoRepository
from app.repositories.empresa_repository import EmpresaRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.auth import RegistroEgresadoRequest, RegistroEmpresaRequest, TokenResponse
from app.security.jwt_provider import create_access_token, create_refresh_token
from app.security.login_rate_limiter import limpiar_intentos, registrar_intento_fallido, verificar_bloqueo
from app.security.password_hasher import hash_password, verify_password
from app.services.email_service import EmailService


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.usuarios = UsuarioRepository(db)
        self.egresados = EgresadoRepository(db)
        self.empresas = EmpresaRepository(db)
        self.email_service = EmailService()

    def registrar_egresado(self, data: RegistroEgresadoRequest) -> Usuario:
        if self.usuarios.existe_correo(data.correo):
            raise ConflictException("El correo electrónico ya está registrado.")
        if self.egresados.existe_ci(data.ci):
            raise ConflictException("Ya existe un egresado registrado con ese CI.")

        usuario = self.usuarios.crear(
            Usuario(correo=data.correo, password_hash=hash_password(data.password), rol=RolNombre.EGRESADO)
        )
        self.egresados.crear(
            PerfilEgresado(
                usuario_id=usuario.id,
                nombres=data.nombres,
                apellidos=data.apellidos,
                ci=data.ci,
                carrera_id=data.carrera_id,
                anio_egreso=data.anio_egreso,
                matricula=data.matricula,
            )
        )
        self.db.commit()
        self.email_service.enviar(
            data.correo, "Verifica tu cuenta en EGRESA", "Gracias por registrarte. Confirma tu cuenta para continuar."
        )
        return usuario

    def registrar_empresa(self, data: RegistroEmpresaRequest) -> Usuario:
        if self.usuarios.existe_correo(data.correo):
            raise ConflictException("El correo electrónico ya está registrado.")
        if self.empresas.existe_nit(data.nit):
            raise ConflictException("Ya existe una empresa registrada con ese NIT/RUC.")

        usuario = self.usuarios.crear(
            Usuario(correo=data.correo, password_hash=hash_password(data.password), rol=RolNombre.EMPRESA)
        )
        self.empresas.crear(
            Empresa(
                usuario_id=usuario.id,
                razon_social=data.razon_social,
                nit=data.nit,
                sector=data.sector,
                direccion=data.direccion,
                telefono=data.telefono,
                representante_legal=data.representante_legal,
                estado_verificacion=EstadoVerificacionEmpresa.PENDIENTE,
            )
        )
        self.db.commit()
        self.email_service.enviar(
            data.correo,
            "Solicitud de registro recibida",
            "Tu empresa fue registrada y está pendiente de autorización por la UAGRM.",
        )
        return usuario

    def login(self, correo: str, password: str) -> tuple[TokenResponse, int]:
        verificar_bloqueo(correo)
        usuario = self.usuarios.obtener_por_correo(correo)
        if usuario is None or not verify_password(password, usuario.password_hash):
            registrar_intento_fallido(correo)
            raise UnauthorizedException("Correo o contraseña incorrectos.")
        if not usuario.activo:
            raise UnauthorizedException("La cuenta se encuentra desactivada.")

        limpiar_intentos(correo)
        subject = str(usuario.id)
        token = TokenResponse(
            access_token=create_access_token(subject, usuario.rol.value),
            refresh_token=create_refresh_token(subject, usuario.rol.value),
            rol=usuario.rol,
        )
        return token, usuario.id
