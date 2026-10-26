"""HU-30: encuesta periódica de situación laboral que la universidad envía a sus egresados."""

import logging
import math
import uuid
from datetime import datetime, time, timezone
from decimal import Decimal

from sqlalchemy import exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException, ConflictException, ForbiddenException, ResourceNotFoundException
from app.core.database import SessionLocal
from app.core.tenancy import condicion_institucion, institucion_efectiva
from app.features.bitacora.service import BitacoraService
from app.features.encuestas.schema import (
    AvanceEncuesta,
    EncuestaCreada,
    EncuestaCreateRequest,
    EncuestaItem,
    EncuestasResponse,
    FormularioEncuesta,
    MiEncuestaItem,
    OpcionEncuesta,
    PreguntaEncuesta,
    RespuestaCreada,
    RespuestaCreateRequest,
    SituacionLaboralCantidad,
)
from app.features.notificaciones.emisor import emitir_notificacion
from app.models.candidato import CandidateEducation, CandidateProfile
from app.models.catalogo import FieldOfStudy
from app.models.encuesta import Survey, SurveyAnswer, SurveyQuestion, SurveyQuestionOption, SurveyResponse
from app.models.usuario import AppUser
from app.security.dependencies import CurrentUser
from app.security.tenant import AlcanceStaff
from app.shared.exportacion import ZONA_BOLIVIA

logger = logging.getLogger(__name__)

TIPO_AVISO = "encuesta_laboral"
# Quienes trabajan responden además dónde y en qué; quienes no, no.
_SITUACIONES_CON_TRABAJO = ("empleado", "independiente")
_PREGUNTAS_DE_TRABAJO = ("empresa", "cargo", "relacion_carrera")
_SITUACIONES = (
    ("empleado", "Empleado/a en una empresa o institución"),
    ("independiente", "Trabajo por cuenta propia o emprendo"),
    ("posgrado", "Estudio un posgrado"),
    ("buscando", "Busco empleo"),
    ("sin_buscar", "No estoy buscando empleo por ahora"),
)
# Las preguntas son las mismas en toda encuesta: son las que alimentan los indicadores de inserción
# laboral (tasa de colocación, tiempo al primer empleo, pertinencia). Cada una tiene un código estable.
_PREGUNTAS = (
    ("situacion_laboral", "¿Cuál es tu situación laboral actual?", "single_choice", True, _SITUACIONES),
    ("empresa", "¿En qué empresa o institución trabajás?", "text", False, ()),
    ("cargo", "¿Qué cargo o actividad desempeñás?", "text", False, ()),
    (
        "relacion_carrera",
        "¿Qué tan relacionado está tu trabajo con tu carrera? (1 = nada, 5 = totalmente)",
        "scale",
        False,
        (),
    ),
    ("meses_primer_empleo", "¿Cuántos meses pasaron desde que te titulaste hasta tu primer empleo?", "number", False, ()),
)
_MAX_MESES = 600


def _igual(columna, valor):
    """`columna = valor`, o `IS NULL` si no hay valor."""
    return columna.is_(None) if valor is None else columna == valor


def _recortar(texto: str, largo: int) -> str:
    return texto if len(texto) <= largo else texto[: largo - 1].rstrip() + "…"


def _vencida(encuesta: Survey, ahora: datetime) -> bool:
    return encuesta.expires_at is not None and encuesta.expires_at <= ahora


def _candidatos(encuesta: Survey):
    """Egresados validados y activos a los que les toca la encuesta."""
    consulta = (
        select(CandidateProfile.id, CandidateProfile.user_id)
        .join(AppUser, AppUser.id == CandidateProfile.user_id)
        .where(CandidateProfile.verification_status == "verified", AppUser.account_status == "active")
    )
    if encuesta.institution_id is not None:
        consulta = consulta.where(condicion_institucion(CandidateProfile.institution_id, encuesta.institution_id))
    if encuesta.field_of_study_id is not None:
        consulta = consulta.where(
            exists().where(
                CandidateEducation.candidate_id == CandidateProfile.id,
                CandidateEducation.field_of_study_id == encuesta.field_of_study_id,
            )
        )
    return consulta


class EncuestaService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.bitacora = BitacoraService(db)

    # ─── Administrador: configurar, enviar y seguir ──────────────────────

    def crear(self, data: EncuestaCreateRequest, alcance: AlcanceStaff, ip: str | None = None) -> EncuestaCreada:
        carrera = None
        if data.carrera_id is not None:
            carrera = self.db.get(FieldOfStudy, data.carrera_id)
            if carrera is None:
                raise ResourceNotFoundException("La carrera elegida no existe.")
        ahora = datetime.now(timezone.utc)
        vence = None
        if data.vence_el is not None:
            vence = datetime.combine(data.vence_el, time.max, tzinfo=ZONA_BOLIVIA)
            if vence <= ahora:
                raise BusinessException("La fecha de cierre tiene que ser posterior a hoy.")
        periodo = data.periodo.strip()
        if not periodo:
            raise BusinessException("Indicá el período que mide la encuesta.")

        repetida = self.db.scalar(
            select(Survey.id).where(
                Survey.is_active.is_(True),
                func.lower(Survey.period) == periodo.lower(),
                _igual(Survey.institution_id, alcance.institution_id),
                _igual(Survey.field_of_study_id, data.carrera_id),
            )
        )
        if repetida is not None:
            raise ConflictException(f"Ya hay una encuesta abierta para el período «{periodo}» con el mismo grupo.")

        if carrera is not None:
            alcance_encuesta = "field_of_study"
        else:
            alcance_encuesta = "institution" if alcance.institution_id is not None else "all_candidates"
        encuesta = Survey(
            title=data.titulo.strip(),
            description=(data.descripcion or "").strip() or None,
            period=periodo,
            target_scope=alcance_encuesta,
            institution_id=alcance.institution_id,
            field_of_study_id=data.carrera_id,
            created_by=alcance.usuario.id_usuario,
            is_active=True,
            starts_at=ahora,
            expires_at=vence,
        )
        destinatarios = self._contar_destinatarios(encuesta)
        if destinatarios == 0:
            raise BusinessException("No hay egresados validados a los que enviarles esta encuesta.")

        for posicion, (codigo, texto, tipo, obligatoria, opciones) in enumerate(_PREGUNTAS, start=1):
            pregunta = SurveyQuestion(
                code=codigo, question_text=texto, question_type=tipo, is_required=obligatoria, position=posicion
            )
            pregunta.options = [
                SurveyQuestionOption(code=cod, option_text=etiqueta, position=n)
                for n, (cod, etiqueta) in enumerate(opciones, start=1)
            ]
            encuesta.questions.append(pregunta)
        self.db.add(encuesta)
        self.db.flush()
        self.bitacora.registrar(
            modulo="encuestas",
            accion="enviar_encuesta",
            usuario_id=alcance.usuario.id_usuario,
            ip=ip,
            detalles=f"encuesta_id={encuesta.id} periodo={periodo} destinatarios={destinatarios}",
        )
        self.db.commit()
        self.db.refresh(encuesta)
        return EncuestaCreada(
            encuesta=self._item(encuesta, ahora),
            mensaje=f"Encuesta enviada a {destinatarios} egresados. Reciben el aviso en sus notificaciones.",
        )

    def listar(self, alcance: AlcanceStaff, page: int, page_size: int) -> EncuestasResponse:
        filtro = [] if alcance.institution_id is None else [Survey.institution_id == alcance.institution_id]
        total = self.db.scalar(select(func.count()).select_from(Survey).where(*filtro)) or 0
        encuestas = self.db.scalars(
            select(Survey)
            .where(*filtro)
            .order_by(Survey.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        ahora = datetime.now(timezone.utc)
        return EncuestasResponse(
            items=[self._item(e, ahora) for e in encuestas],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=max(1, math.ceil(total / page_size)),
        )

    def avance(self, encuesta_id: uuid.UUID, alcance: AlcanceStaff) -> AvanceEncuesta:
        encuesta = self._obtener_de_staff(encuesta_id, alcance)
        item = self._item(encuesta, datetime.now(timezone.utc))
        filas = self.db.execute(
            select(SurveyQuestionOption.code, func.count(SurveyAnswer.id))
            .join(SurveyAnswer, SurveyAnswer.selected_option_id == SurveyQuestionOption.id)
            .join(SurveyResponse, SurveyResponse.id == SurveyAnswer.response_id)
            .join(SurveyQuestion, SurveyQuestion.id == SurveyAnswer.question_id)
            .where(SurveyResponse.survey_id == encuesta.id, SurveyQuestion.code == "situacion_laboral")
            .group_by(SurveyQuestionOption.code)
        ).all()
        cantidades = {codigo: cantidad for codigo, cantidad in filas}
        return AvanceEncuesta(
            encuesta=item,
            pendientes=max(item.destinatarios - item.respondieron, 0),
            situacion_laboral=[
                SituacionLaboralCantidad(codigo=codigo, etiqueta=etiqueta, cantidad=cantidades.get(codigo, 0))
                for codigo, etiqueta in _SITUACIONES
            ],
        )

    def cerrar(self, encuesta_id: uuid.UUID, alcance: AlcanceStaff, ip: str | None = None) -> EncuestaItem:
        encuesta = self._obtener_de_staff(encuesta_id, alcance)
        if not encuesta.is_active:
            raise BusinessException("La encuesta ya estaba cerrada.")
        encuesta.is_active = False
        self.bitacora.registrar(
            modulo="encuestas",
            accion="cerrar_encuesta",
            usuario_id=alcance.usuario.id_usuario,
            ip=ip,
            detalles=f"encuesta_id={encuesta.id} periodo={encuesta.period}",
        )
        self.db.commit()
        self.db.refresh(encuesta)
        return self._item(encuesta, datetime.now(timezone.utc))

    # ─── Egresado: recibir y responder ───────────────────────────────────

    def mias(self, current_user: CurrentUser) -> list[MiEncuestaItem]:
        perfil = self._perfil(current_user)
        if perfil.verification_status != "verified":
            return []
        mis_carreras = select(CandidateEducation.field_of_study_id).where(
            CandidateEducation.candidate_id == perfil.id, CandidateEducation.field_of_study_id.is_not(None)
        )
        universidad = institucion_efectiva(perfil.institution_id)
        encuestas = self.db.scalars(
            select(Survey)
            .where(
                or_(Survey.institution_id.is_(None), Survey.institution_id == universidad),
                or_(Survey.field_of_study_id.is_(None), Survey.field_of_study_id.in_(mis_carreras)),
            )
            .order_by(Survey.created_at.desc())
        ).all()
        respondidas = {
            survey_id: fecha
            for survey_id, fecha in self.db.execute(
                select(SurveyResponse.survey_id, SurveyResponse.submitted_at).where(
                    SurveyResponse.candidate_id == perfil.id
                )
            )
        }
        ahora = datetime.now(timezone.utc)
        items = []
        for e in encuestas:
            fecha = respondidas.get(e.id)
            # Una encuesta cerrada o vencida solo se muestra si el egresado ya la había respondido.
            if fecha is None and (not e.is_active or _vencida(e, ahora)):
                continue
            items.append(
                MiEncuestaItem(
                    id=e.id,
                    titulo=e.title,
                    descripcion=e.description,
                    periodo=e.period,
                    vence_el=e.expires_at,
                    respondida=fecha is not None,
                    respondida_el=fecha,
                )
            )
        return items

    def formulario(self, encuesta_id: uuid.UUID, current_user: CurrentUser) -> FormularioEncuesta:
        perfil = self._perfil(current_user)
        encuesta = self._obtener_para_candidato(encuesta_id, perfil)
        if self._ya_respondio(encuesta.id, perfil.id):
            raise ConflictException("Ya respondiste la encuesta de este período.")
        self._exigir_abierta(encuesta)
        return FormularioEncuesta(
            id=encuesta.id,
            titulo=encuesta.title,
            descripcion=encuesta.description,
            periodo=encuesta.period,
            vence_el=encuesta.expires_at,
            preguntas=[
                PreguntaEncuesta(
                    id=p.id,
                    codigo=p.code,
                    texto=p.question_text,
                    tipo=p.question_type,
                    obligatoria=p.is_required,
                    opciones=[OpcionEncuesta(id=o.id, codigo=o.code, texto=o.option_text) for o in p.options],
                )
                for p in encuesta.questions
            ],
        )

    def responder(
        self,
        encuesta_id: uuid.UUID,
        data: RespuestaCreateRequest,
        current_user: CurrentUser,
        ip: str | None = None,
    ) -> RespuestaCreada:
        perfil = self._perfil(current_user)
        encuesta = self._obtener_para_candidato(encuesta_id, perfil)
        if self._ya_respondio(encuesta.id, perfil.id):
            raise ConflictException("Ya respondiste la encuesta de este período.")
        self._exigir_abierta(encuesta)

        respuesta = SurveyResponse(survey_id=encuesta.id, candidate_id=perfil.id)
        respuesta.answers = self._validar(encuesta, data)
        self.db.add(respuesta)
        self.bitacora.registrar(
            modulo="encuestas",
            accion="responder_encuesta",
            usuario_id=current_user.id_usuario,
            ip=ip,
            detalles=f"encuesta_id={encuesta.id} periodo={encuesta.period}",
        )
        try:
            self.db.commit()
        except IntegrityError as exc:
            # Dos envíos a la vez del mismo egresado: gana el primero.
            self.db.rollback()
            raise ConflictException("Ya respondiste la encuesta de este período.") from exc
        self.db.refresh(respuesta)
        return RespuestaCreada(mensaje="¡Gracias! Tu respuesta quedó registrada.", respondida_el=respuesta.submitted_at)

    # ─── Internos ────────────────────────────────────────────────────────

    def _contar_destinatarios(self, encuesta: Survey) -> int:
        return self.db.scalar(select(func.count()).select_from(_candidatos(encuesta).subquery())) or 0

    def _item(self, encuesta: Survey, ahora: datetime) -> EncuestaItem:
        destinatarios = self._contar_destinatarios(encuesta)
        respondieron = (
            self.db.scalar(
                select(func.count()).select_from(SurveyResponse).where(SurveyResponse.survey_id == encuesta.id)
            )
            or 0
        )
        porcentaje = min(100.0, round(100 * respondieron / destinatarios, 1)) if destinatarios else 0.0
        alcance = {"field_of_study": "carrera", "institution": "universidad"}.get(encuesta.target_scope, "todas")
        return EncuestaItem(
            id=encuesta.id,
            titulo=encuesta.title,
            descripcion=encuesta.description,
            periodo=encuesta.period,
            alcance=alcance,
            carrera=encuesta.field_of_study.name if encuesta.field_of_study is not None else None,
            enviada_el=encuesta.starts_at or encuesta.created_at,
            vence_el=encuesta.expires_at,
            activa=encuesta.is_active,
            abierta=encuesta.is_active and not _vencida(encuesta, ahora),
            destinatarios=destinatarios,
            respondieron=respondieron,
            porcentaje=porcentaje,
        )

    def _obtener_de_staff(self, encuesta_id: uuid.UUID, alcance: AlcanceStaff) -> Survey:
        encuesta = self.db.get(Survey, encuesta_id)
        # Una encuesta de otra universidad se trata como inexistente.
        if encuesta is None or (
            alcance.institution_id is not None and encuesta.institution_id != alcance.institution_id
        ):
            raise ResourceNotFoundException("La encuesta no existe.")
        return encuesta

    def _perfil(self, current_user: CurrentUser) -> CandidateProfile:
        perfil = self.db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == current_user.id_usuario))
        if perfil is None:
            raise ForbiddenException("Solo los egresados responden la encuesta de situación laboral.")
        return perfil

    def _obtener_para_candidato(self, encuesta_id: uuid.UUID, perfil: CandidateProfile) -> Survey:
        """La encuesta si le corresponde al egresado; si no, es como si no existiera."""
        encuesta = self.db.get(Survey, encuesta_id)
        if encuesta is None or perfil.verification_status != "verified":
            raise ResourceNotFoundException("La encuesta no existe.")
        if (
            encuesta.institution_id is not None
            and institucion_efectiva(perfil.institution_id) != encuesta.institution_id
        ):
            raise ResourceNotFoundException("La encuesta no existe.")
        if encuesta.field_of_study_id is not None:
            en_la_carrera = self.db.scalar(
                select(
                    exists().where(
                        CandidateEducation.candidate_id == perfil.id,
                        CandidateEducation.field_of_study_id == encuesta.field_of_study_id,
                    )
                )
            )
            if not en_la_carrera:
                raise ResourceNotFoundException("La encuesta no existe.")
        return encuesta

    def _ya_respondio(self, encuesta_id: uuid.UUID, candidato_id: uuid.UUID) -> bool:
        return (
            self.db.scalar(
                select(SurveyResponse.id).where(
                    SurveyResponse.survey_id == encuesta_id, SurveyResponse.candidate_id == candidato_id
                )
            )
            is not None
        )

    @staticmethod
    def _exigir_abierta(encuesta: Survey) -> None:
        if not encuesta.is_active or _vencida(encuesta, datetime.now(timezone.utc)):
            raise BusinessException("Esta encuesta ya está cerrada.")

    @staticmethod
    def _validar(encuesta: Survey, data: RespuestaCreateRequest) -> list[SurveyAnswer]:
        """Revisa cada respuesta contra su pregunta y arma las filas a guardar."""
        preguntas = {p.id: p for p in encuesta.questions}
        por_pregunta: dict[uuid.UUID, SurveyAnswer] = {}
        for r in data.respuestas:
            pregunta = preguntas.get(r.pregunta_id)
            if pregunta is None:
                raise BusinessException("Una de las respuestas no corresponde a esta encuesta.")
            if r.pregunta_id in por_pregunta:
                raise BusinessException("Hay una pregunta respondida dos veces.")
            respuesta = EncuestaService._respuesta(pregunta, r)
            if respuesta is not None:
                por_pregunta[pregunta.id] = respuesta

        for pregunta in encuesta.questions:
            if pregunta.is_required and pregunta.id not in por_pregunta:
                raise BusinessException(f"Falta responder: {pregunta.question_text}")

        situacion = next(
            (
                o.code
                for p in encuesta.questions
                if p.code == "situacion_laboral" and p.id in por_pregunta
                for o in p.options
                if o.id == por_pregunta[p.id].selected_option_id
            ),
            None,
        )
        de_trabajo = [p for p in encuesta.questions if p.code in _PREGUNTAS_DE_TRABAJO]
        if situacion in _SITUACIONES_CON_TRABAJO:
            for pregunta in de_trabajo:
                if pregunta.id not in por_pregunta:
                    raise BusinessException(f"Falta responder: {pregunta.question_text}")
        else:
            # Quien no trabaja no tiene empresa, cargo ni pertinencia que declarar.
            for pregunta in de_trabajo:
                por_pregunta.pop(pregunta.id, None)
        return list(por_pregunta.values())

    @staticmethod
    def _respuesta(pregunta: SurveyQuestion, r) -> SurveyAnswer | None:
        """La fila de una respuesta ya validada; None si la dejó en blanco."""
        if pregunta.question_type == "single_choice":
            if r.opcion_id is None:
                return None
            if r.opcion_id not in {o.id for o in pregunta.options}:
                raise BusinessException("Elegiste una opción que no existe en esa pregunta.")
            return SurveyAnswer(question_id=pregunta.id, selected_option_id=r.opcion_id)
        if pregunta.question_type == "text":
            texto = (r.texto or "").strip()
            return SurveyAnswer(question_id=pregunta.id, answer_text=texto) if texto else None
        if r.numero is None:
            return None
        if pregunta.question_type == "scale":
            if r.numero != int(r.numero) or not 1 <= r.numero <= 5:
                raise BusinessException("La relación con tu carrera se responde con un número del 1 al 5.")
        elif not 0 <= r.numero <= _MAX_MESES:
            raise BusinessException(f"Los meses tienen que estar entre 0 y {_MAX_MESES}.")
        return SurveyAnswer(question_id=pregunta.id, answer_number=Decimal(str(r.numero)))


def avisar_encuesta(db: Session, encuesta_id: uuid.UUID) -> int:
    """Manda el aviso (campanita y push, según sus preferencias) a cada egresado al que le toca."""
    encuesta = db.get(Survey, encuesta_id)
    if encuesta is None:
        return 0
    vence = ""
    if encuesta.expires_at is not None:
        vence = f" Podés responderla hasta el {encuesta.expires_at.astimezone(ZONA_BOLIVIA):%d/%m/%Y}."
    avisados = 0
    for _, usuario_id in db.execute(_candidatos(encuesta)).all():
        emitir_notificacion(
            db,
            usuario_id,
            TIPO_AVISO,
            _recortar(f"Encuesta de situación laboral · {encuesta.period}", 200),
            "Tu universidad te pide unos minutos para actualizar tu situación laboral." + vence,
            f"/encuestas/{encuesta.id}",
        )
        avisados += 1
        if avisados % 50 == 0:
            db.commit()
    db.commit()
    return avisados


def avisar_encuesta_en_segundo_plano(encuesta_id: uuid.UUID) -> None:
    """Para BackgroundTasks: corre después de responder, con su propia sesión.

    Si falla, la encuesta ya quedó enviada y cada egresado la sigue viendo en «Mis encuestas».
    """
    try:
        with SessionLocal() as db:
            avisados = avisar_encuesta(db, encuesta_id)
        logger.info("Encuesta %s: se avisó a %s egresados.", encuesta_id, avisados)
    except Exception:
        logger.exception("No se pudo avisar la encuesta %s.", encuesta_id)
