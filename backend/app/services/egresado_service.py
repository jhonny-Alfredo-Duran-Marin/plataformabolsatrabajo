import json

from sqlalchemy.orm import Session

from app.common.exceptions import ResourceNotFoundException
from app.models.egresado import PerfilEgresado
from app.models.enums import EstadoValidacionEgresado
from app.repositories.egresado_repository import EgresadoRepository
from app.schemas.egresado import PerfilEgresadoUpdateRequest, VisibilidadPerfilRequest
from app.services.email_service import EmailService

CAMPOS_COMPLETITUD = (
    "telefono",
    "direccion",
    "fecha_nacimiento",
    "carrera_id",
    "anio_egreso",
    "estado_laboral",
    "cv_url",
    "disponibilidad",
)


class EgresadoService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = EgresadoRepository(db)
        self.email_service = EmailService()

    def obtener_por_usuario(self, usuario_id: int) -> PerfilEgresado:
        perfil = self.repo.obtener_por_usuario_id(usuario_id)
        if perfil is None:
            raise ResourceNotFoundException("No se encontró el perfil del egresado.")
        return perfil

    def actualizar_perfil(self, usuario_id: int, data: PerfilEgresadoUpdateRequest) -> PerfilEgresado:
        perfil = self.obtener_por_usuario(usuario_id)
        for campo, valor in data.model_dump(exclude_unset=True).items():
            setattr(perfil, campo, valor)
        perfil.porcentaje_completitud = self._calcular_completitud(perfil)
        self.db.commit()
        return perfil

    def actualizar_visibilidad(self, usuario_id: int, data: VisibilidadPerfilRequest) -> PerfilEgresado:
        perfil = self.obtener_por_usuario(usuario_id)
        perfil.perfil_oculto = data.perfil_oculto
        perfil.visibilidad_secciones = json.dumps(data.secciones_visibles)
        self.db.commit()
        return perfil

    def listar_pendientes_validacion(self) -> list[PerfilEgresado]:
        return self.repo.listar_pendientes_validacion()

    def validar(self, perfil_id: int, aprobado: bool, motivo_rechazo: str | None) -> PerfilEgresado:
        perfil = self.repo.obtener_por_id(perfil_id)
        if perfil is None:
            raise ResourceNotFoundException("No se encontró el perfil del egresado.")

        perfil.estado_validacion = (
            EstadoValidacionEgresado.APROBADO if aprobado else EstadoValidacionEgresado.RECHAZADO
        )
        perfil.motivo_rechazo = None if aprobado else motivo_rechazo
        self.db.commit()
        return perfil

    @staticmethod
    def _calcular_completitud(perfil: PerfilEgresado) -> int:
        completados = sum(1 for campo in CAMPOS_COMPLETITUD if getattr(perfil, campo))
        return round(completados / len(CAMPOS_COMPLETITUD) * 100)
