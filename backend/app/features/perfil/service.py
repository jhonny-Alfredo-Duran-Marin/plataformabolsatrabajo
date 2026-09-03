import json
import uuid
from datetime import date, datetime

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
from app.models.candidato import CandidateEducation, CandidateLanguage, Certification, WorkExperience
from app.models.candidato import CandidateProfile
from app.shared.email_service import EmailService

_ESTADOS_VALIDACION = {
    "verified": "APROBADO",
    "rejected": "RECHAZADO",
}
_ESTADOS_BUSQUEDA = {"actively_looking", "open_to_offers", "not_looking"}

# El esquema real de candidate_education/work_experience/candidate_language usa códigos
# en inglés con CHECK constraints fijos; el frontend actual maneja etiquetas en español
# libres. Estos mapas traducen en ambas direcciones con un fallback seguro.
_ACADEMIC_STATUS_ES_A_EN = {
    "en curso": "in_progress",
    "cursando": "in_progress",
    "concluido": "completed",
    "completado": "completed",
    "terminado": "completed",
    "egresado": "graduated",
    "graduado": "graduated",
    "abandonado": "withdrawn",
    "retirado": "withdrawn",
}
_ACADEMIC_STATUS_VALIDOS = {"in_progress", "completed", "graduated", "withdrawn"}
_ACADEMIC_STATUS_EN_A_ES = {
    "in_progress": "en curso",
    "completed": "concluido",
    "graduated": "egresado",
    "withdrawn": "abandonado",
}

_NIVEL_IDIOMA_ES_A_EN = {
    "basico": "basic",
    "básico": "basic",
    "intermedio": "intermediate",
    "avanzado": "advanced",
    "fluido": "fluent",
    "nativo": "native",
}
_NIVELES_IDIOMA_VALIDOS = {"basic", "intermediate", "advanced", "fluent", "native"}
_NIVEL_IDIOMA_EN_A_ES = {
    "basic": "basico",
    "intermediate": "intermedio",
    "advanced": "avanzado",
    "fluent": "fluido",
    "native": "nativo",
}

_MARCADOR_EDUCACION_REGISTRO = EgresadoRepository.MARCADOR_EDUCACION_REGISTRO
_MATRICULA_PREFIJO = "Matrícula: "


def _descripcion_educacion_registro(matricula: str | None) -> str:
    if matricula:
        return f"{_MARCADOR_EDUCACION_REGISTRO} {_MATRICULA_PREFIJO}{matricula}"
    return _MARCADOR_EDUCACION_REGISTRO

# Secciones que HU-09 pide ocultar/mostrar de forma granular. "datos_contacto" se
# sostiene en la columna contact_visibility (ya existía); el resto se persiste en
# la columna JSONB candidate_profile.section_visibility (agregada vía migración).
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


def _normalizar_estado_academico(valor: str | None) -> str:
    if not valor:
        return "in_progress"
    limpio = valor.strip().lower()
    if limpio in _ACADEMIC_STATUS_VALIDOS:
        return limpio
    return _ACADEMIC_STATUS_ES_A_EN.get(limpio, "in_progress")


def _normalizar_nivel_idioma(valor: str | None) -> str:
    if not valor:
        return "basic"
    limpio = valor.strip().lower()
    if limpio in _NIVELES_IDIOMA_VALIDOS:
        return limpio
    return _NIVEL_IDIOMA_ES_A_EN.get(limpio, "basic")


def _secciones_de(perfil: CandidateProfile) -> dict[str, bool]:
    secciones = {seccion: True for seccion in _SECCIONES_PERFIL}
    secciones.update(perfil.section_visibility or {})
    secciones["datos_contacto"] = perfil.contact_visibility
    return secciones


def _a_dto_formacion(item: CandidateEducation) -> FormacionResponse:
    return FormacionResponse(
        id=item.id,
        institucion=item.institution_name or "",
        programa=item.program_name,
        estado_academico=_ACADEMIC_STATUS_EN_A_ES.get(item.academic_status, item.academic_status),
        fecha_inicio=item.start_date,
        fecha_fin=item.end_date,
    )


def _a_dto_experiencia(item: WorkExperience) -> ExperienciaResponse:
    return ExperienciaResponse(
        id=item.id,
        empresa=item.company_name or "",
        cargo=item.position_title,
        descripcion=item.description,
        fecha_inicio=item.start_date,
        fecha_fin=item.end_date,
    )


def _a_dto_idioma(item: CandidateLanguage, nombre_idioma: str) -> IdiomaResponse:
    return IdiomaResponse(
        id=item.language_id,
        idioma=nombre_idioma,
        nivel=_NIVEL_IDIOMA_EN_A_ES.get(item.proficiency_level, item.proficiency_level),
    )


def _a_dto_certificacion(item: Certification) -> CertificacionResponse:
    return CertificacionResponse(
        id=item.id, nombre=item.name, entidad_emisora=item.issuer, fecha_obtencion=item.issued_at
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

        if datos.get("estado_laboral") in _ESTADOS_BUSQUEDA:
            perfil.job_search_status = datos["estado_laboral"]

        if datos.get("disponibilidad") is not None:
            perfil.availability = datos["disponibilidad"]

        # carrera_id/anio_egreso/matricula no tienen columna en candidate_profile: se
        # reflejan en la fila "principal" de candidate_education (ver repo).
        if any(datos.get(campo) is not None for campo in ("carrera_id", "anio_egreso", "matricula")):
            self._actualizar_educacion_principal(
                perfil,
                carrera_id=datos.get("carrera_id"),
                anio_egreso=datos.get("anio_egreso"),
                matricula=datos.get("matricula"),
            )

        self.db.commit()
        return self._a_dto(perfil)

    def _actualizar_educacion_principal(
        self,
        perfil: CandidateProfile,
        carrera_id: uuid.UUID | None,
        anio_egreso: int | None,
        matricula: str | None,
    ) -> None:
        item = self.repo.obtener_educacion_principal(perfil.id)
        if item is None:
            item = CandidateEducation(
                candidate_id=perfil.id,
                program_name="Carrera universitaria",
                education_level="undergraduate",
                academic_status="graduated",
                description=_descripcion_educacion_registro(matricula),
            )
            self.repo.crear_formacion(item)
        elif matricula is not None:
            item.description = _descripcion_educacion_registro(matricula)
        if carrera_id is not None:
            item.field_of_study_id = carrera_id
        if anio_egreso is not None:
            item.graduation_date = date(anio_egreso, 12, 31)

    def actualizar_visibilidad(
        self, usuario_id: uuid.UUID | str, data: VisibilidadPerfilRequest
    ) -> PerfilEgresadoResponse:
        perfil = self._obtener_perfil(usuario_id)
        perfil.profile_visibility = "private" if data.perfil_oculto else "platform"

        if "datos_contacto" in data.secciones_visibles:
            perfil.contact_visibility = bool(data.secciones_visibles["datos_contacto"])

        otras_secciones = {
            seccion: bool(valor)
            for seccion, valor in data.secciones_visibles.items()
            if seccion in _SECCIONES_PERFIL and seccion != "datos_contacto"
        }
        if otras_secciones:
            perfil.section_visibility = {**(perfil.section_visibility or {}), **otras_secciones}

        self.db.commit()
        return self._a_dto(perfil)

    def listar_pendientes_validacion(self) -> list[PerfilEgresadoResponse]:
        perfiles = self.repo.listar_pendientes_validacion()
        ids = [perfil.id for perfil in perfiles]
        cantidad_habilidades = self.repo.cantidad_habilidades_de(ids)
        educacion_principal = self.repo.educacion_principal_de(ids)
        return [
            self._dto_desde_datos(perfil, cantidad_habilidades.get(perfil.id, 0), educacion_principal.get(perfil.id))
            for perfil in perfiles
        ]

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
            education_level="undergraduate",
            academic_status=_normalizar_estado_academico(data.estado_academico),
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
        # El frontend actual no recolecta fecha de inicio ni tipo de empleo, pero
        # work_experience los exige NOT NULL: se aplican valores por defecto razonables.
        item = WorkExperience(
            candidate_id=perfil.id,
            company_name=data.empresa,
            position_title=data.cargo,
            employment_type="full_time",
            start_date=data.fecha_inicio or date.today(),
            end_date=data.fecha_fin,
            currently_working=data.fecha_fin is None,
            description=data.descripcion,
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
        return [_a_dto_idioma(cl, lang.name) for cl, lang in self.repo.listar_idiomas(perfil.id)]

    def crear_idioma(self, usuario_id: uuid.UUID | str, data: IdiomaRequest) -> IdiomaResponse:
        perfil = self._obtener_perfil(usuario_id)
        idioma = self.repo.obtener_o_crear_idioma(data.idioma.strip())
        existente = self.repo.obtener_idioma(perfil.id, idioma.id)
        if existente is not None:
            existente.proficiency_level = _normalizar_nivel_idioma(data.nivel)
            item = existente
        else:
            item = CandidateLanguage(
                candidate_id=perfil.id,
                language_id=idioma.id,
                proficiency_level=_normalizar_nivel_idioma(data.nivel),
            )
            self.repo.crear_idioma(item)
        self.db.commit()
        return _a_dto_idioma(item, idioma.name)

    def eliminar_idioma(self, usuario_id: uuid.UUID | str, item_id: uuid.UUID | str) -> None:
        perfil = self._obtener_perfil(usuario_id)
        item = self.repo.obtener_idioma(perfil.id, item_id)
        if item is None:
            raise ResourceNotFoundException("No se encontró el idioma.")
        self.repo.eliminar_idioma(item)
        self.db.commit()

    # --- Certificaciones ---
    def listar_certificaciones(self, usuario_id: uuid.UUID | str) -> list[CertificacionResponse]:
        perfil = self._obtener_perfil(usuario_id)
        return [_a_dto_certificacion(item) for item in self.repo.listar_certificaciones(perfil.id)]

    def crear_certificacion(self, usuario_id: uuid.UUID | str, data: CertificacionRequest) -> CertificacionResponse:
        perfil = self._obtener_perfil(usuario_id)
        item = Certification(
            candidate_id=perfil.id, name=data.nombre, issuer=data.entidad_emisora, issued_at=data.fecha_obtencion
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
        educacion_principal = self.repo.obtener_educacion_principal(perfil.id)

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
        anio_egreso = educacion_principal.graduation_date.year if educacion_principal and educacion_principal.graduation_date else None
        pdf.cell(0, 6, f"Año de egreso: {anio_egreso or 's/d'}", ln=True)
        for item in formaciones:
            rango = " - ".join(filter(None, [str(item.start_date or ""), str(item.end_date or "")]))
            pdf.cell(0, 6, f"{item.program_name} · {item.institution_name or ''} ({rango or 's/f'})", ln=True)
        pdf.ln(2)

        if experiencias:
            titulo_seccion("Experiencia laboral")
            pdf.set_font("Helvetica", "", 10)
            for item in experiencias:
                rango = " - ".join(filter(None, [str(item.start_date or ""), str(item.end_date or "actualidad")]))
                pdf.cell(0, 6, f"{item.position_title} · {item.company_name or ''} ({rango})", ln=True)
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
            for cl, lang in idiomas:
                pdf.cell(0, 6, f"{lang.name} - {cl.proficiency_level}", ln=True)
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
        cantidad_habilidades = len(self.repo.listar_habilidades(perfil.id))
        educacion_principal = self.repo.obtener_educacion_principal(perfil.id)
        return self._dto_desde_datos(perfil, cantidad_habilidades, educacion_principal)

    def _dto_desde_datos(
        self,
        perfil: CandidateProfile,
        cantidad_habilidades: int,
        educacion_principal: CandidateEducation | None,
    ) -> PerfilEgresadoResponse:
        secciones = _secciones_de(perfil)

        carrera_id = educacion_principal.field_of_study_id if educacion_principal else None
        anio_egreso = (
            educacion_principal.graduation_date.year
            if educacion_principal and educacion_principal.graduation_date
            else None
        )
        matricula = None
        if educacion_principal and educacion_principal.description and _MATRICULA_PREFIJO in educacion_principal.description:
            matricula = educacion_principal.description.split(_MATRICULA_PREFIJO, 1)[1]

        campos_obligatorios = (
            bool(carrera_id),
            bool(anio_egreso),
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
            carrera_id=carrera_id,
            anio_egreso=anio_egreso,
            matricula=matricula,
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
