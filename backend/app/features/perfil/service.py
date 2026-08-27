import json
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.common.exceptions import ResourceNotFoundException
from app.features.auth.repository import UsuarioRepository
from app.features.perfil.repository import EgresadoRepository
from app.features.perfil.schema import (
    CertificacionRequest,
    CertificacionResponse,
    ExperienciaRequest,
    ExperienciaResponse,
    FormacionRequest,
    FormacionResponse,
    HabilidadResponse,
    HabilidadesRequest,
    IdiomaRequest,
    IdiomaResponse,
    PerfilEgresadoResponse,
    PerfilEgresadoUpdateRequest,
    VisibilidadPerfilRequest,
)
from app.models.candidato import (
    CandidateCertification,
    CandidateEducation,
    CandidateExperience,
    CandidateLanguage,
    CandidateProfile,
)
from app.shared.email_service import EmailService

_ESTADOS_VALIDACION = {
    "verified": "APROBADO",
    "rejected": "RECHAZADO",
}
_ESTADOS_BUSQUEDA = {"actively_looking", "open_to_offers", "not_looking"}
_NIVELES_DISPONIBILIDAD = {"inmediata", "1_semana", "2_semanas", "1_mes"}
_SECCIONES_PERFIL = (
    "datos_contacto",
    "experiencia_laboral",
    "formacion_adicional",
    "idiomas",
    "certificaciones",
    "habilidades",
)


def _nombre_archivo_cv(nombres: str, apellidos: str) -> str:
    import unicodedata

    def _limpiar(texto: str) -> str:
        sin_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
        return "".join(parte.capitalize() for parte in sin_acentos.split())

    return f"{_limpiar(nombres)}{_limpiar(apellidos)}_CV.pdf"


def _secciones_de(perfil: CandidateProfile) -> dict[str, bool]:
    try:
        guardadas = json.loads(perfil.section_visibility) if perfil.section_visibility else {}
    except (TypeError, ValueError):
        guardadas = {}
    secciones = {seccion: True for seccion in _SECCIONES_PERFIL}
    secciones.update({k: bool(v) for k, v in guardadas.items() if k in _SECCIONES_PERFIL})
    secciones["datos_contacto"] = perfil.contact_visibility
    return secciones


def _a_dto_formacion(item: CandidateEducation) -> FormacionResponse:
    return FormacionResponse(
        id=item.id,
        institucion=item.institution_name,
        programa=item.program_name,
        estado_academico=item.academic_status,
        fecha_inicio=item.start_date,
        fecha_fin=item.end_date,
    )


def _a_dto_experiencia(item: CandidateExperience) -> ExperienciaResponse:
    return ExperienciaResponse(
        id=item.id,
        empresa=item.company_name,
        cargo=item.position,
        descripcion=item.description,
        fecha_inicio=item.start_date,
        fecha_fin=item.end_date,
    )


def _a_dto_idioma(item: CandidateLanguage) -> IdiomaResponse:
    return IdiomaResponse(id=item.id, idioma=item.language_name, nivel=item.proficiency_level)


def _a_dto_certificacion(item: CandidateCertification) -> CertificacionResponse:
    return CertificacionResponse(
        id=item.id, nombre=item.name, entidad_emisora=item.issuer, fecha_obtencion=item.issued_date
    )


class EgresadoService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = EgresadoRepository(db)
        self.usuarios = UsuarioRepository(db)
        self.email_service = EmailService()

    def obtener_por_usuario(self, usuario_id: uuid.UUID | str) -> PerfilEgresadoResponse:
        perfil = self._obtener_perfil(usuario_id)
        return self._a_dto(perfil)

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
        if datos.get("carrera_id") is not None:
            perfil.field_of_study_id = datos["carrera_id"]
        if datos.get("anio_egreso") is not None:
            perfil.graduation_year = datos["anio_egreso"]
        if datos.get("matricula") is not None:
            perfil.student_id_code = datos["matricula"]

        if datos.get("estado_laboral") in _ESTADOS_BUSQUEDA:
            perfil.job_search_status = datos["estado_laboral"]
        if datos.get("disponibilidad") is not None:
            perfil.availability = datos["disponibilidad"]

        self.db.commit()
        return self._a_dto(perfil)

    def actualizar_visibilidad(
        self, usuario_id: uuid.UUID | str, data: VisibilidadPerfilRequest
    ) -> PerfilEgresadoResponse:
        perfil = self._obtener_perfil(usuario_id)
        perfil.profile_visibility = "private" if data.perfil_oculto else "platform"

        secciones_actuales = _secciones_de(perfil)
        secciones_actuales.update(
            {k: bool(v) for k, v in data.secciones_visibles.items() if k in _SECCIONES_PERFIL}
        )
        perfil.contact_visibility = secciones_actuales["datos_contacto"]
        perfil.section_visibility = json.dumps(secciones_actuales)

        self.db.commit()
        return self._a_dto(perfil)

    def listar_pendientes_validacion(self) -> list[PerfilEgresadoResponse]:
        return [self._a_dto(perfil) for perfil in self.repo.listar_pendientes_validacion()]

    def validar(self, perfil_id: uuid.UUID | str, aprobado: bool, motivo_rechazo: str | None) -> PerfilEgresadoResponse:
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

        return self._a_dto(perfil)

    # --- Formación académica ---
    def listar_formacion(self, usuario_id: uuid.UUID | str) -> list[FormacionResponse]:
        perfil = self._obtener_perfil(usuario_id)
        return [_a_dto_formacion(item) for item in self.repo.listar_formacion(perfil.id)]

    def crear_formacion(self, usuario_id: uuid.UUID | str, data: FormacionRequest) -> FormacionResponse:
        perfil = self._obtener_perfil(usuario_id)
        item = CandidateEducation(
            candidate_id=perfil.id,
            institution_name=data.institucion,
            program_name=data.programa,
            academic_status=data.estado_academico,
            start_date=data.fecha_inicio,
            end_date=data.fecha_fin,
        )
        self.repo.crear_formacion(item)
        self.db.commit()
        return _a_dto_formacion(item)

    def eliminar_formacion(self, usuario_id: uuid.UUID | str, item_id: uuid.UUID | str) -> None:
        perfil = self._obtener_perfil(usuario_id)
        item = self.repo.obtener_formacion(item_id)
        if item is None or item.candidate_id != perfil.id:
            raise ResourceNotFoundException("No se encontró el registro de formación.")
        self.repo.eliminar_formacion(item)
        self.db.commit()

    # --- Experiencia laboral ---
    def listar_experiencia(self, usuario_id: uuid.UUID | str) -> list[ExperienciaResponse]:
        perfil = self._obtener_perfil(usuario_id)
        return [_a_dto_experiencia(item) for item in self.repo.listar_experiencia(perfil.id)]

    def crear_experiencia(self, usuario_id: uuid.UUID | str, data: ExperienciaRequest) -> ExperienciaResponse:
        perfil = self._obtener_perfil(usuario_id)
        item = CandidateExperience(
            candidate_id=perfil.id,
            company_name=data.empresa,
            position=data.cargo,
            description=data.descripcion,
            start_date=data.fecha_inicio,
            end_date=data.fecha_fin,
        )
        self.repo.crear_experiencia(item)
        self.db.commit()
        return _a_dto_experiencia(item)

    def eliminar_experiencia(self, usuario_id: uuid.UUID | str, item_id: uuid.UUID | str) -> None:
        perfil = self._obtener_perfil(usuario_id)
        item = self.repo.obtener_experiencia(item_id)
        if item is None or item.candidate_id != perfil.id:
            raise ResourceNotFoundException("No se encontró el registro de experiencia.")
        self.repo.eliminar_experiencia(item)
        self.db.commit()

    # --- Idiomas ---
    def listar_idiomas(self, usuario_id: uuid.UUID | str) -> list[IdiomaResponse]:
        perfil = self._obtener_perfil(usuario_id)
        return [_a_dto_idioma(item) for item in self.repo.listar_idiomas(perfil.id)]

    def crear_idioma(self, usuario_id: uuid.UUID | str, data: IdiomaRequest) -> IdiomaResponse:
        perfil = self._obtener_perfil(usuario_id)
        item = CandidateLanguage(candidate_id=perfil.id, language_name=data.idioma, proficiency_level=data.nivel)
        self.repo.crear_idioma(item)
        self.db.commit()
        return _a_dto_idioma(item)

    def eliminar_idioma(self, usuario_id: uuid.UUID | str, item_id: uuid.UUID | str) -> None:
        perfil = self._obtener_perfil(usuario_id)
        item = self.repo.obtener_idioma(item_id)
        if item is None or item.candidate_id != perfil.id:
            raise ResourceNotFoundException("No se encontró el idioma.")
        self.repo.eliminar_idioma(item)
        self.db.commit()

    # --- Certificaciones ---
    def listar_certificaciones(self, usuario_id: uuid.UUID | str) -> list[CertificacionResponse]:
        perfil = self._obtener_perfil(usuario_id)
        return [_a_dto_certificacion(item) for item in self.repo.listar_certificaciones(perfil.id)]

    def crear_certificacion(self, usuario_id: uuid.UUID | str, data: CertificacionRequest) -> CertificacionResponse:
        perfil = self._obtener_perfil(usuario_id)
        item = CandidateCertification(
            candidate_id=perfil.id, name=data.nombre, issuer=data.entidad_emisora, issued_date=data.fecha_obtencion
        )
        self.repo.crear_certificacion(item)
        self.db.commit()
        return _a_dto_certificacion(item)

    def eliminar_certificacion(self, usuario_id: uuid.UUID | str, item_id: uuid.UUID | str) -> None:
        perfil = self._obtener_perfil(usuario_id)
        item = self.repo.obtener_certificacion(item_id)
        if item is None or item.candidate_id != perfil.id:
            raise ResourceNotFoundException("No se encontró la certificación.")
        self.repo.eliminar_certificacion(item)
        self.db.commit()

    # --- Habilidades ---
    def listar_habilidades(self, usuario_id: uuid.UUID | str) -> list[HabilidadResponse]:
        perfil = self._obtener_perfil(usuario_id)
        return [
            HabilidadResponse(id=skill.id, nombre=skill.name, categoria=skill.category)
            for skill in self.repo.listar_habilidades(perfil.id)
        ]

    def actualizar_habilidades(self, usuario_id: uuid.UUID | str, data: HabilidadesRequest) -> list[HabilidadResponse]:
        perfil = self._obtener_perfil(usuario_id)
        nombres_normalizados = [nombre.strip() for nombre in data.habilidades if nombre.strip()]
        skill_ids = [self.repo.obtener_o_crear_habilidad(nombre).id for nombre in nombres_normalizados]
        self.repo.reemplazar_habilidades(perfil.id, skill_ids)
        self.db.commit()
        return self.listar_habilidades(usuario_id)

    def generar_cv_pdf(self, usuario_id: uuid.UUID | str) -> tuple[bytes, str]:
        from fpdf import FPDF

        perfil = self._obtener_perfil(usuario_id)
        usuario = self.usuarios.obtener_por_id(usuario_id)
        formaciones = self.repo.listar_formacion(perfil.id)
        experiencias = self.repo.listar_experiencia(perfil.id)
        idiomas = self.repo.listar_idiomas(perfil.id)
        certificaciones = self.repo.listar_certificaciones(perfil.id)
        habilidades = self.repo.listar_habilidades(perfil.id)

        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.add_page()

        pdf.set_font("Helvetica", "B", 18)
        pdf.cell(0, 12, f"{perfil.first_name} {perfil.last_name}", ln=True)

        pdf.set_font("Helvetica", "", 11)
        contacto = " | ".join(
            filter(None, [perfil.phone, usuario.email if usuario else None, perfil.city])
        )
        if contacto:
            pdf.cell(0, 8, contacto, ln=True)
        if perfil.professional_headline:
            pdf.set_font("Helvetica", "I", 11)
            pdf.cell(0, 8, perfil.professional_headline, ln=True)
        pdf.ln(2)

        def titulo_seccion(texto: str) -> None:
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 9, texto, ln=True)
            pdf.set_draw_color(180, 180, 180)
            pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y())
            pdf.ln(2)

        if perfil.professional_summary:
            titulo_seccion("Resumen profesional")
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 6, perfil.professional_summary)
            pdf.ln(2)

        titulo_seccion("Formación académica")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, f"Año de egreso: {perfil.graduation_year or '—'}", ln=True)
        for item in formaciones:
            rango = " - ".join(filter(None, [str(item.start_date or ""), str(item.end_date or "")]))
            pdf.cell(0, 6, f"{item.program_name} · {item.institution_name} ({rango or 's/f'})", ln=True)
        pdf.ln(2)

        if experiencias:
            titulo_seccion("Experiencia laboral")
            pdf.set_font("Helvetica", "", 10)
            for item in experiencias:
                rango = " - ".join(filter(None, [str(item.start_date or ""), str(item.end_date or "actualidad")]))
                pdf.cell(0, 6, f"{item.position} · {item.company_name} ({rango})", ln=True)
                if item.description:
                    pdf.multi_cell(0, 5, item.description)
            pdf.ln(2)

        if habilidades:
            titulo_seccion("Habilidades")
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 6, ", ".join(skill.name for skill in habilidades))
            pdf.ln(2)

        if idiomas:
            titulo_seccion("Idiomas")
            pdf.set_font("Helvetica", "", 10)
            for item in idiomas:
                pdf.cell(0, 6, f"{item.language_name} — {item.proficiency_level}", ln=True)
            pdf.ln(2)

        if certificaciones:
            titulo_seccion("Certificaciones")
            pdf.set_font("Helvetica", "", 10)
            for item in certificaciones:
                emisor = f" ({item.issuer})" if item.issuer else ""
                pdf.cell(0, 6, f"{item.name}{emisor}", ln=True)

        nombre_archivo = _nombre_archivo_cv(perfil.first_name, perfil.last_name)
        return bytes(pdf.output()), nombre_archivo

    def _a_dto(self, perfil: CandidateProfile) -> PerfilEgresadoResponse:
        secciones = _secciones_de(perfil)
        cantidad_habilidades = len(self.repo.listar_habilidades(perfil.id))

        campos_obligatorios = (
            bool(perfil.field_of_study_id),
            bool(perfil.graduation_year),
            cantidad_habilidades > 0,
            bool(perfil.availability),
        )
        campos_extra = (
            bool(perfil.phone),
            bool(perfil.professional_headline),
            bool(perfil.professional_summary),
            bool(perfil.portfolio_url),
        )
        todos = campos_obligatorios + campos_extra
        porcentaje = round(sum(1 for campo in todos if campo) / len(todos) * 100)

        return PerfilEgresadoResponse(
            id=perfil.id,
            usuario_id=perfil.user_id,
            nombres=perfil.first_name,
            apellidos=perfil.last_name,
            ci=perfil.document_number,
            telefono=perfil.phone,
            carrera_id=perfil.field_of_study_id,
            anio_egreso=perfil.graduation_year,
            matricula=perfil.student_id_code,
            disponibilidad=perfil.availability,
            estado_validacion=_ESTADOS_VALIDACION.get(perfil.verification_status, "PENDIENTE"),
            porcentaje_completitud=porcentaje,
            perfil_oculto=perfil.profile_visibility == "private",
            visibilidad_secciones=json.dumps(secciones),
            ciudad=perfil.city,
            titulo_profesional=perfil.professional_headline,
            resumen_profesional=perfil.professional_summary,
        )

    def _obtener_perfil(self, usuario_id: uuid.UUID | str) -> CandidateProfile:
        perfil = self.repo.obtener_por_usuario_id(usuario_id)
        if perfil is None:
            raise ResourceNotFoundException("No se encontró el perfil del egresado.")
        return perfil
