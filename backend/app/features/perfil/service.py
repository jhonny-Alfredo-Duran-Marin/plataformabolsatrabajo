import json
import uuid

from sqlalchemy.orm import Session

from app.common.exceptions import ResourceNotFoundException
from app.features.auth.repository import UsuarioRepository
from app.features.perfil.repository import EgresadoRepository
from app.features.perfil.schema import (
    PerfilEgresadoResponse,
    PerfilEgresadoUpdateRequest,
    VisibilidadPerfilRequest,
)
from app.models.candidato import CandidateProfile
from app.shared.email_service import EmailService

_ESTADOS_VALIDACION = {
    "verified": "APROBADO",
    "rejected": "RECHAZADO",
}
_ESTADOS_BUSQUEDA = {"actively_looking", "open_to_offers", "not_looking"}
_CAMPOS_COMPLETITUD = ("phone", "professional_headline", "professional_summary", "portfolio_url", "document_number")


def _a_dto(perfil: CandidateProfile) -> PerfilEgresadoResponse:
    completados = sum(1 for campo in _CAMPOS_COMPLETITUD if getattr(perfil, campo))
    secciones = {"datos_contacto": perfil.contact_visibility}
    return PerfilEgresadoResponse(
        id=perfil.id,
        usuario_id=perfil.user_id,
        nombres=perfil.first_name,
        apellidos=perfil.last_name,
        ci=perfil.document_number,
        telefono=perfil.phone,
        estado_validacion=_ESTADOS_VALIDACION.get(perfil.verification_status, "PENDIENTE"),
        porcentaje_completitud=round(completados / len(_CAMPOS_COMPLETITUD) * 100),
        perfil_oculto=perfil.profile_visibility == "private",
        visibilidad_secciones=json.dumps(secciones),
        ciudad=perfil.city,
        titulo_profesional=perfil.professional_headline,
        resumen_profesional=perfil.professional_summary,
    )


class EgresadoService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = EgresadoRepository(db)
        self.usuarios = UsuarioRepository(db)
        self.email_service = EmailService()

    def obtener_por_usuario(self, usuario_id: uuid.UUID | str) -> PerfilEgresadoResponse:
        perfil = self._obtener_perfil(usuario_id)
        return _a_dto(perfil)

    def actualizar_perfil(self, usuario_id: uuid.UUID | str, data: PerfilEgresadoUpdateRequest) -> PerfilEgresadoResponse:
        perfil = self._obtener_perfil(usuario_id)
        datos = data.model_dump(exclude_unset=True)

        if datos.get("telefono") is not None:
            perfil.phone = datos["telefono"]
        if datos.get("ciudad") is not None:
            perfil.city = datos["ciudad"]
        if datos.get("url_redes_profesionales") is not None:
            perfil.portfolio_url = datos["url_redes_profesionales"]
        if datos.get("titulo_profesional") is not None:
            perfil.professional_headline = datos["titulo_profesional"]
        if datos.get("resumen_profesional") is not None:
            perfil.professional_summary = datos["resumen_profesional"]

        nuevo_estado = datos.get("estado_laboral") or datos.get("disponibilidad")
        if nuevo_estado in _ESTADOS_BUSQUEDA:
            perfil.job_search_status = nuevo_estado

        self.db.commit()
        return _a_dto(perfil)

    def actualizar_visibilidad(
        self, usuario_id: uuid.UUID | str, data: VisibilidadPerfilRequest
    ) -> PerfilEgresadoResponse:
        perfil = self._obtener_perfil(usuario_id)
        perfil.profile_visibility = "private" if data.perfil_oculto else "platform"
        perfil.contact_visibility = bool(data.secciones_visibles.get("datos_contacto", True))
        self.db.commit()
        return _a_dto(perfil)

    def listar_pendientes_validacion(self) -> list[PerfilEgresadoResponse]:
        return [_a_dto(perfil) for perfil in self.repo.listar_pendientes_validacion()]

    def validar(self, perfil_id: uuid.UUID | str, aprobado: bool, motivo_rechazo: str | None) -> PerfilEgresadoResponse:
        from datetime import datetime

        perfil = self.repo.obtener_por_id(perfil_id)
        if perfil is None:
            raise ResourceNotFoundException("No se encontró el perfil del egresado.")

        perfil.verification_status = "verified" if aprobado else "rejected"
        perfil.verified_at = datetime.now() if aprobado else None
        self.db.commit()

        usuario = self.usuarios.obtener_por_id(perfil.user_id)
        if usuario is not None:
            if aprobado:
                asunto = "Tu validación como egresado fue aprobada"
                cuerpo = "Tu perfil fue validado por la universidad. Ya puedes postularte a vacantes."
            else:
                asunto = "Tu validación como egresado fue rechazada"
                cuerpo = f"Tu solicitud de validación fue rechazada. Motivo: {motivo_rechazo or 'no especificado'}."
            self.email_service.enviar(usuario.email, asunto, cuerpo)

        return _a_dto(perfil)

    def _obtener_perfil(self, usuario_id: uuid.UUID | str) -> CandidateProfile:
        perfil = self.repo.obtener_por_usuario_id(usuario_id)
        if perfil is None:
            raise ResourceNotFoundException("No se encontró el perfil del egresado.")
        return perfil
