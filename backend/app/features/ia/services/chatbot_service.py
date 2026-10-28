"""Chatbot de orientación (HU-28, módulo 5.1.13).

Asistente conversacional para resolver dudas sobre el uso de EGRESA y consultar el
estado real de las postulaciones de la cuenta autenticada.

Reglas de negocio y criterios de aceptación (HU-28):
1. Cualquier usuario autenticado puede abrir el chatbot y hacer preguntas en lenguaje
   natural sobre el uso de la plataforma.
2. El egresado puede consultar el estado de sus propias postulaciones y recibir una
   respuesta basada en datos reales de su cuenta.
3. El chatbot nunca expone datos de otro usuario distinto al que está consultando.
4. Si el chatbot no puede responder una consulta (fuera de alcance), lo indica
   claramente y no inventa información (CP03).
5. Toda interacción queda registrada en `chatbot_session` y `chatbot_message` para
   fines de mejora del servicio, sin exponerla a otros usuarios.
6. Si el microservicio/asistente de IA no está disponible, responde 503 informando que
   el asistente no está disponible temporalmente (CP04).
"""

import logging
import re
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.common.exceptions import (
    AppException,
    BusinessException,
    ForbiddenException,
    ServiceUnavailableException,
)
from app.core.config import get_settings
from app.features.ia.schema import (
    ChatbotConsultaRequest,
    ChatbotMensajeDTO,
    ChatbotRespuestaResponse,
    ChatbotSesionResponse,
    EnlaceUtilChatbotDTO,
    PostulacionResumenChatbotDTO,
)
from app.features.ia.services import afinidad as motor_afinidad
from app.features.postulaciones.schema import ESTADOS_INFO
from app.models.candidato import CandidateProfile
from app.models.chatbot import ChatbotMessage, ChatbotSession
from app.models.empresa import Company
from app.models.entrevista import Interview
from app.models.postulacion import Application
from app.models.usuario import AppUser
from app.models.vacante import JobPosting
from app.security.dependencies import CurrentUser

logger = logging.getLogger(__name__)

MENSAJE_CHATBOT_NO_DISPONIBLE = (
    "El asistente de orientación no está disponible temporalmente. "
    "Podés consultar el Centro de ayuda o intentar de nuevo más tarde."
)

MENSAJE_FUERA_DE_ALCANCE = (
    "No puedo responder esa consulta porque está fuera de mi alcance. "
    "Soy el asistente de orientación de EGRESA y solo puedo ayudarte con dudas sobre "
    "el uso de la plataforma y el estado real de tus postulaciones, sin inventar información."
)

MENSAJE_PRIVACIDAD = (
    "Por seguridad y privacidad, solo puedo consultar información asociada a tu propia cuenta. "
    "Nunca expongo postulaciones ni datos personales de otros usuarios."
)

_RE_EMAIL = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


def chatbot_activo() -> bool:
    """Indica si el microservicio del chatbot de orientación está habilitado."""
    s = get_settings()
    return bool(s.ia_chatbot_activo and s.ia_recomendaciones_activas)


def _normalizar(texto: str) -> str:
    """Convierte a minúsculas y quita tildes/diacríticos para comparar intenciones."""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFKD", texto.lower()) if not unicodedata.combining(c)
    )
    return re.sub(r"[^\w\s@.-]", " ", sin_tildes)


def _sugerencias_por_rol(rol: str) -> list[str]:
    if rol == "empresa":
        return [
            "¿Cómo publico una vacante?",
            "¿Cómo gestiono el proceso de selección?",
            "¿Cómo veo sugerencias de candidatos con IA?",
            "¿Cómo genero reportes personalizados?",
        ]
    if rol in ("platform_admin", "moderator"):
        return [
            "¿Cómo valido a un egresado?",
            "¿Cómo modero las vacantes y denuncias?",
            "¿Cómo funcionan las copias de seguridad?",
            "¿Cómo abro la bitácora confidencial?",
        ]
    return [
        "¿Cómo me postulo a una vacante?",
        "¿Cuál es el estado de mis postulaciones?",
        "¿Cómo se calcula el porcentaje de afinidad?",
        "¿Cómo completo mi perfil profesional y CV?",
    ]


def _saludo_por_rol(rol: str) -> str:
    if rol == "empresa":
        return (
            "¡Hola! Soy el asistente de orientación de EGRESA. Puedo ayudarte con la publicación "
            "de vacantes, el tablero de selección, las sugerencias de candidatos y el uso de la plataforma."
        )
    if rol in ("platform_admin", "moderator"):
        return (
            "¡Hola! Soy el asistente de orientación de EGRESA. Puedo orientarte sobre validación de "
            "egresados, moderación de ofertas, reportes, bitácora, respaldos y administración."
        )
    return (
        "¡Hola! Soy el asistente de orientación de EGRESA. Preguntame cómo usar la plataforma, "
        "cómo postularte a una vacante o cuál es el estado actual de tus postulaciones."
    )


@dataclass
class _ResultadoIntencion:
    intencion: str
    en_alcance: bool
    texto: str
    postulaciones: list[PostulacionResumenChatbotDTO] = field(default_factory=list)
    enlaces: list[EnlaceUtilChatbotDTO] = field(default_factory=list)
    sugerencias: list[str] = field(default_factory=list)


class ChatbotService:
    def __init__(self, db: Session | None = None) -> None:
        self.db = db

    def abrir_sesion(
        self,
        usuario: CurrentUser,
        session_id: uuid.UUID | None = None,
        nueva: bool = False,
    ) -> ChatbotSesionResponse:
        """Obtiene la sesión activa del usuario (o crea una nueva) con su historial propio."""
        self._verificar_disponibilidad()
        assert self.db is not None

        try:
            sesion = self._obtener_o_crear_sesion(usuario.id_usuario, session_id=session_id, forzar_nueva=nueva)
            self.db.commit()
            self.db.refresh(sesion)
        except AppException:
            raise
        except Exception as exc:
            logger.exception("Falló al abrir sesión del chatbot")
            raise ServiceUnavailableException(MENSAJE_CHATBOT_NO_DISPONIBLE) from exc

        mensajes_dto = [
            ChatbotMensajeDTO(
                id=m.id,
                role=m.message_role,
                content=m.content,
                created_at=m.created_at,
            )
            for m in sesion.messages
            if m.message_role in ("user", "assistant")
        ]

        return ChatbotSesionResponse(
            session_id=sesion.id,
            started_at=sesion.started_at,
            ended_at=sesion.ended_at,
            saludo=_saludo_por_rol(usuario.rol),
            sugerencias=_sugerencias_por_rol(usuario.rol),
            mensajes=mensajes_dto,
        )

    def consultar(self, usuario: CurrentUser, data: ChatbotConsultaRequest) -> ChatbotRespuestaResponse:
        """Procesa una pregunta en lenguaje natural, registra la interacción y responde."""
        self._verificar_disponibilidad()
        assert self.db is not None

        pregunta = data.mensaje.strip()
        if not pregunta:
            raise BusinessException("Escribí una consulta para que el asistente pueda ayudarte.")

        try:
            sesion = self._obtener_o_crear_sesion(usuario.id_usuario, session_id=data.session_id, forzar_nueva=False)
            resultado = self._procesar_consulta(usuario, pregunta)

            msg_usuario = ChatbotMessage(
                session_id=sesion.id,
                message_role="user",
                content=pregunta,
            )
            msg_asistente = ChatbotMessage(
                session_id=sesion.id,
                message_role="assistant",
                content=resultado.texto,
            )
            self.db.add(msg_usuario)
            self.db.add(msg_asistente)
            self.db.commit()
            self.db.refresh(msg_usuario)
            self.db.refresh(msg_asistente)
        except AppException:
            raise
        except Exception as exc:
            logger.exception("Falló al procesar consulta del chatbot")
            raise ServiceUnavailableException(MENSAJE_CHATBOT_NO_DISPONIBLE) from exc

        return ChatbotRespuestaResponse(
            session_id=sesion.id,
            mensaje_usuario=ChatbotMensajeDTO(
                id=msg_usuario.id,
                role=msg_usuario.message_role,
                content=msg_usuario.content,
                created_at=msg_usuario.created_at,
            ),
            respuesta=ChatbotMensajeDTO(
                id=msg_asistente.id,
                role=msg_asistente.message_role,
                content=msg_asistente.content,
                created_at=msg_asistente.created_at,
            ),
            intencion=resultado.intencion,
            en_alcance=resultado.en_alcance,
            postulaciones=resultado.postulaciones,
            sugerencias=resultado.sugerencias or _sugerencias_por_rol(usuario.rol),
            enlaces_utiles=resultado.enlaces,
        )

    def responder(self, usuario_id: uuid.UUID, mensaje: str, rol: str = "candidate") -> str:
        """Método directo compatible con llamadas internas de servicio."""
        self._verificar_disponibilidad()
        usuario = CurrentUser(id_usuario=usuario_id, rol=rol, roles=[rol])
        if self.db is not None:
            res = self.consultar(usuario, ChatbotConsultaRequest(mensaje=mensaje))
            return res.respuesta.content
        return self._procesar_consulta(usuario, mensaje).texto

    # ─── Auxiliares de sesión y disponibilidad ─────────────────────────────────

    @staticmethod
    def _verificar_disponibilidad() -> None:
        if not chatbot_activo():
            raise ServiceUnavailableException(MENSAJE_CHATBOT_NO_DISPONIBLE)

    def _obtener_o_crear_sesion(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID | None = None,
        forzar_nueva: bool = False,
    ) -> ChatbotSession:
        assert self.db is not None

        if forzar_nueva:
            abiertas = self.db.scalars(
                select(ChatbotSession).where(
                    ChatbotSession.user_id == user_id,
                    ChatbotSession.ended_at.is_(None),
                )
            ).all()
            ahora = datetime.now(timezone.utc)
            for s in abiertas:
                s.ended_at = ahora
            nueva = ChatbotSession(user_id=user_id)
            self.db.add(nueva)
            self.db.flush()
            return nueva

        if session_id is not None:
            existente = self.db.scalar(
                select(ChatbotSession)
                .options(joinedload(ChatbotSession.messages))
                .where(ChatbotSession.id == session_id)
            )
            if existente is not None:
                # CA3: nunca exponer ni permitir usar sesiones de otro usuario
                if existente.user_id != user_id:
                    raise ForbiddenException("No tenés permiso para acceder a la conversación de otro usuario.")
                return existente

        activa = self.db.scalar(
            select(ChatbotSession)
            .options(joinedload(ChatbotSession.messages))
            .where(
                ChatbotSession.user_id == user_id,
                ChatbotSession.ended_at.is_(None),
            )
            .order_by(ChatbotSession.started_at.desc())
        )
        if activa is not None:
            return activa

        nueva = ChatbotSession(user_id=user_id)
        self.db.add(nueva)
        self.db.flush()
        return nueva

    # ─── Motor de clasificación y respuesta ────────────────────────────────────

    def _procesar_consulta(self, usuario: CurrentUser, pregunta_original: str) -> _ResultadoIntencion:
        norm = _normalizar(pregunta_original)
        palabras = set(norm.split())

        # 1. Control estricto de privacidad: nunca exponer datos de otro usuario (CA3)
        if self._intenta_consultar_otro_usuario(usuario.id_usuario, pregunta_original, norm):
            return _ResultadoIntencion(
                intencion="privacidad_denegada",
                en_alcance=True,
                texto=MENSAJE_PRIVACIDAD,
                sugerencias=_sugerencias_por_rol(usuario.rol),
            )

        # 2. CP01: ¿Cómo postularse a una vacante? (flujo y pasos de postulación)
        if self._es_consulta_como_postular(norm, palabras):
            return self._responder_como_postular()

        # 3. CP02: Consultar el estado real de las postulaciones de la cuenta del egresado
        if self._es_consulta_estado_postulaciones(norm, palabras):
            return self._responder_estado_postulaciones(usuario, norm)

        # 4. Significado de estados o cómo retirar una postulación
        if self._es_consulta_retirar_o_significado_estados(norm, palabras):
            return self._responder_significado_estados_y_retiro()

        # 5. Perfil profesional, CV y visibilidad
        if self._es_consulta_perfil(norm, palabras):
            return self._responder_perfil(usuario)

        # 6. Afinidad y recomendaciones de IA (HU-23)
        if self._es_consulta_afinidad_recomendaciones(norm, palabras):
            return self._responder_afinidad_recomendaciones()

        # 7. Entrevistas y mensajería con empresas (HU-19, HU-20)
        if self._es_consulta_entrevistas_mensajes(norm, palabras):
            return self._responder_entrevistas_y_mensajes(usuario)

        # 8. Notificaciones y avisos push (HU-21)
        if self._es_consulta_notificaciones(norm, palabras):
            return self._responder_notificaciones()

        # 9. Denunciar oferta sospechosa / moderación antifraude (HU-22)
        if self._es_consulta_denuncias(norm, palabras):
            return self._responder_denuncias()

        # 10. Validación institucional de cuenta (egresado o empresa)
        if self._es_consulta_validacion(norm, palabras):
            return self._responder_validacion()

        # 11. Empresas: publicar vacantes y proceso de selección
        if self._es_consulta_empresa_vacantes_seleccion(norm, palabras):
            return self._responder_empresa_vacantes_seleccion()

        # 12. Reportes personalizados
        if self._es_consulta_reportes(norm, palabras):
            return self._responder_reportes()

        # 13. Administración: bitácora, respaldos, tareas, grupos, planes
        if self._es_consulta_administracion(norm, palabras):
            return self._responder_administracion()

        # 14. Cuenta, contraseña y seguridad de sesión
        if self._es_consulta_cuenta_seguridad(norm, palabras):
            return self._responder_cuenta_seguridad()

        # 15. Búsqueda de vacantes general
        if self._es_consulta_buscar_vacantes(norm, palabras):
            return self._responder_buscar_vacantes()

        # 16. Saludo o pedido general de ayuda sobre la plataforma
        if self._es_saludo_o_ayuda_general(norm, palabras):
            return _ResultadoIntencion(
                intencion="saludo_ayuda",
                en_alcance=True,
                texto=(
                    f"{_saludo_por_rol(usuario.rol)}\n\n"
                    "Podés preguntarme, por ejemplo:\n"
                    "• ¿Cómo me postulo a una vacante?\n"
                    "• ¿Cuál es el estado de mis postulaciones?\n"
                    "• ¿Cómo completo mi perfil y subo mi CV?\n"
                    "• ¿Cómo funciona el porcentaje de afinidad?\n"
                    "• ¿Cómo confirmo una entrevista o hablo con una empresa?"
                ),
                enlaces=[EnlaceUtilChatbotDTO(texto="Abrir Centro de ayuda", ruta="/ayuda")],
                sugerencias=_sugerencias_por_rol(usuario.rol),
            )

        # 17. CP03: Fuera del alcance del chatbot (no inventa información)
        return _ResultadoIntencion(
            intencion="fuera_de_alcance",
            en_alcance=False,
            texto=MENSAJE_FUERA_DE_ALCANCE,
            enlaces=[EnlaceUtilChatbotDTO(texto="Ver Centro de ayuda", ruta="/ayuda")],
            sugerencias=_sugerencias_por_rol(usuario.rol),
        )

    # ─── Detectores de intención ───────────────────────────────────────────────

    def _intenta_consultar_otro_usuario(
        self,
        usuario_id: uuid.UUID,
        pregunta_original: str,
        norm: str,
    ) -> bool:
        """Detecta si la pregunta pide datos o postulaciones de otra persona distinta al usuario actual."""
        # Si incluye un correo electrónico distinto al propio
        correos = _RE_EMAIL.findall(pregunta_original.lower())
        if correos and self.db is not None:
            user = self.db.scalar(select(AppUser).where(AppUser.id == usuario_id))
            correo_propio = (user.email or "").lower() if user else ""
            if any(c != correo_propio for c in correos):
                return True

        patrones_ajenos = (
            r"\b(otro|otra|otros|otras)\s+(usuario|usuarios|egresado|egresados|candidato|candidatos|persona|personas|compa[nñ]ero|estudiante)\b",
            r"\bpostulaciones\s+de\s+(?!mi\s+cuenta\b|mi\s+perfil\b|mis\b)[a-z0-9_]+",
            r"\bestado\s+de\s+las\s+postulaciones\s+de\b",
            r"\bdatos\s+(personales\s+)?de\s+(otro|otra|juan|pedro|ana|maria|carlos|luis|jose|sofia|diego)\b",
            r"\bcorreo\s+de\s+(otro|otra|juan|pedro|ana|maria|carlos|luis)\b",
            r"\btelefono\s+de\s+(otro|otra|juan|pedro|ana|maria|carlos|luis)\b",
            r"\bcuenta\s+ajena\b",
            r"\bde\s+mi\s+(amigo|amiga|compa[nñ]ero|compa[nñ]era|hermano|hermana)\b",
        )
        return any(re.search(p, norm) for p in patrones_ajenos)

    @staticmethod
    def _es_consulta_como_postular(norm: str, palabras: set[str]) -> bool:
        frases_como = (
            "como postular",
            "como me postulo",
            "como postularme",
            "como postularse",
            "como puedo postular",
            "pasos para postular",
            "flujo de postulacion",
            "proceso para postular",
            "proceso de postulacion",
            "como aplicar a una vacante",
            "como aplicar a una oferta",
            "como me inscribo a una vacante",
            "donde me postulo",
            "donde postular",
            "quiero postularme",
            "requisitos para postular",
            "que necesito para postular",
            "enviar postulacion",
            "enviar mi postulacion",
        )
        if any(f in norm for f in frases_como):
            return True
        tiene_como = bool(palabras & {"como", "pasos", "donde", "instrucciones", "guia", "flujo"})
        tiene_postular = any(
            p.startswith("postula") or p in {"aplicar", "aplico"} for p in palabras
        )
        # Si pregunta "¿cómo van mis postulaciones?" o "¿cómo están mis postulaciones?" es estado (CP02)
        if any(f in norm for f in ("como van mis postulacion", "como estan mis postulacion", "como va mi postulacion")):
            return False
        return tiene_como and tiene_postular

    @staticmethod
    def _es_consulta_estado_postulaciones(norm: str, palabras: set[str]) -> bool:
        frases_estado = (
            "estado de mis postulaciones",
            "estado de mi postulacion",
            "mis postulaciones",
            "mi postulacion",
            "como van mis postulaciones",
            "como va mi postulacion",
            "como estan mis postulaciones",
            "cuales son mis postulaciones",
            "ver mis postulaciones",
            "consultar mis postulaciones",
            "postulaciones activas",
            "en que etapa estoy",
            "en que etapa esta mi postulacion",
            "en que estado esta mi postulacion",
            "a que vacantes me postule",
            "a que ofertas me postule",
            "seguimiento de mis postulaciones",
            "seguimiento de mi postulacion",
            "resultado de mi postulacion",
            "resultado de mis postulaciones",
            "tengo postulaciones",
            "mis solicitudes de empleo",
            "estado de postulaciones",
        )
        if any(f in norm for f in frases_estado):
            return True
        tiene_postulacion = any(p.startswith("postulacion") for p in palabras)
        tiene_estado_o_posesivo = bool(
            palabras & {"estado", "estados", "mis", "mi", "etapa", "etapas", "activas", "avance", "seguimiento"}
        )
        if "significa" in palabras or "significan" in palabras or "retirar" in palabras or "cancelar" in palabras:
            return False
        return tiene_postulacion and tiene_estado_o_posesivo

    @staticmethod
    def _es_consulta_retirar_o_significado_estados(norm: str, palabras: set[str]) -> bool:
        if any(
            f in norm
            for f in (
                "que significa cada estado",
                "significado de los estados",
                "que significan los estados",
                "retirar postulacion",
                "retirar mi postulacion",
                "cancelar postulacion",
                "cancelar mi postulacion",
                "darme de baja de una postulacion",
            )
        ):
            return True
        return bool(palabras & {"retirar", "retirarme"}) and any(p.startswith("postula") for p in palabras)

    @staticmethod
    def _es_consulta_perfil(norm: str, palabras: set[str]) -> bool:
        return bool(
            palabras & {"perfil", "cv", "curriculum", "hoja", "habilidades", "visibilidad", "privacidad", "idiomas", "formacion"}
        ) and not ("vacante" in palabras and "crear" in palabras)

    @staticmethod
    def _es_consulta_afinidad_recomendaciones(norm: str, palabras: set[str]) -> bool:
        return bool(palabras & {"afinidad", "recomendaciones", "recomendadas", "recomendada", "matching", "porcentaje"})

    @staticmethod
    def _es_consulta_entrevistas_mensajes(norm: str, palabras: set[str]) -> bool:
        return bool(palabras & {"entrevista", "entrevistas", "mensaje", "mensajes", "mensajeria", "chat", "reprogramar"})

    @staticmethod
    def _es_consulta_notificaciones(norm: str, palabras: set[str]) -> bool:
        return bool(palabras & {"notificacion", "notificaciones", "avisos", "campana", "push", "alertas", "boletin"})

    @staticmethod
    def _es_consulta_denuncias(norm: str, palabras: set[str]) -> bool:
        return bool(palabras & {"denunciar", "denuncia", "denuncias", "sospechosa", "fraude", "falsa", "estafa"})

    @staticmethod
    def _es_consulta_validacion(norm: str, palabras: set[str]) -> bool:
        return bool(palabras & {"validacion", "validar", "validado", "verificacion", "verificar", "pendiente", "titulo"})

    @staticmethod
    def _es_consulta_empresa_vacantes_seleccion(norm: str, palabras: set[str]) -> bool:
        if any(
            f in norm
            for f in (
                "publicar vacante",
                "publicar una vacante",
                "crear vacante",
                "crear una vacante",
                "proceso de seleccion",
                "pipeline",
                "kanban",
                "comparar candidatos",
                "sugerencias de candidatos",
                "preguntas de filtro",
            )
        ):
            return True
        return bool(palabras & {"seleccion", "pipeline", "kanban", "reclutar", "reclutamiento"})

    @staticmethod
    def _es_consulta_reportes(norm: str, palabras: set[str]) -> bool:
        return bool(palabras & {"reporte", "reportes", "exportar", "excel", "pdf", "estadisticas"})

    @staticmethod
    def _es_consulta_administracion(norm: str, palabras: set[str]) -> bool:
        return bool(
            palabras
            & {
                "bitacora",
                "respaldo",
                "respaldos",
                "backup",
                "backups",
                "restaurar",
                "grupos",
                "permisos",
                "planes",
                "moderador",
                "moderadores",
                "tareas",
            }
        )

    @staticmethod
    def _es_consulta_cuenta_seguridad(norm: str, palabras: set[str]) -> bool:
        return bool(palabras & {"contrasena", "clave", "password", "bloqueo", "bloqueada", "sesion", "inactividad", "login"})

    @staticmethod
    def _es_consulta_buscar_vacantes(norm: str, palabras: set[str]) -> bool:
        return bool(palabras & {"vacante", "vacantes", "oferta", "ofertas", "empleo", "empleos", "trabajo", "buscar"})

    @staticmethod
    def _es_saludo_o_ayuda_general(norm: str, palabras: set[str]) -> bool:
        saludos = {"hola", "buenas", "buen", "saludos", "ayuda", "orientacion", "asistente", "egresa", "menu", "opciones"}
        if palabras & saludos and len(palabras) <= 6:
            return True
        return any(
            f in norm
            for f in (
                "que podes hacer",
                "que puedes hacer",
                "en que me ayudas",
                "como funciona egresa",
                "como uso la plataforma",
                "como funciona la plataforma",
                "para que servis",
                "quien sos",
            )
        )

    # ─── Generadores de respuesta ──────────────────────────────────────────────

    @staticmethod
    def _responder_como_postular() -> _ResultadoIntencion:
        texto = (
            "Para postularte a una vacante en EGRESA seguí estos pasos:\n\n"
            "1. **Explorá las ofertas:** Ingresá a **«Buscar vacantes»** (`/vacantes`) o a **«Vacantes recomendadas»** (`/recomendaciones`) y filtrá por puesto, habilidad, ciudad o modalidad.\n"
            "2. **Revisá el detalle y tu afinidad:** Abrí la vacante que te interese para conocer sus requisitos, condiciones y el porcentaje de afinidad con tu perfil profesional.\n"
            "3. **Enviá tu postulación:** Tocá el botón **«Postularme»**, respondé las preguntas de filtro de la empresa (si la oferta las incluye) y confirmá el envío. *(Recordá que tu cuenta de egresado debe estar validada por tu universidad).* \n"
            "4. **Hacé seguimiento:** Consultá el avance de etapa, entrevistas y mensajes en **«Mis postulaciones»** (`/postulaciones`) o preguntándome directamente *«¿Cuál es el estado de mis postulaciones?»*."
        )
        return _ResultadoIntencion(
            intencion="como_postular",
            en_alcance=True,
            texto=texto,
            enlaces=[
                EnlaceUtilChatbotDTO(texto="Buscar vacantes", ruta="/vacantes"),
                EnlaceUtilChatbotDTO(texto="Vacantes recomendadas", ruta="/recomendaciones"),
                EnlaceUtilChatbotDTO(texto="Mis postulaciones", ruta="/postulaciones"),
            ],
            sugerencias=[
                "¿Cuál es el estado de mis postulaciones?",
                "¿Qué significa cada estado de postulación?",
                "¿Cómo se calcula el porcentaje de afinidad?",
            ],
        )

    def _responder_estado_postulaciones(self, usuario: CurrentUser, norm: str) -> _ResultadoIntencion:
        if self.db is None:
            return _ResultadoIntencion(
                intencion="estado_postulaciones",
                en_alcance=True,
                texto="Para consultar tus postulaciones necesitás tener una sesión activa.",
            )

        candidato = self.db.scalar(
            select(CandidateProfile).where(CandidateProfile.user_id == usuario.id_usuario)
        )
        if candidato is None:
            if usuario.rol == "empresa":
                return _ResultadoIntencion(
                    intencion="estado_postulaciones",
                    en_alcance=True,
                    texto=(
                        "Tu cuenta tiene perfil de **Empresa**, por lo que no registra postulaciones propias de egresado. "
                        "Si querés revisar y avanzar a los candidatos que se postularon a tus ofertas, ingresá a **«Proceso de Selección»** (`/seleccion`)."
                    ),
                    enlaces=[
                        EnlaceUtilChatbotDTO(texto="Proceso de Selección", ruta="/seleccion"),
                        EnlaceUtilChatbotDTO(texto="Mis Vacantes", ruta="/vacantes/mis-vacantes"),
                    ],
                )
            if usuario.rol in ("platform_admin", "moderator"):
                return _ResultadoIntencion(
                    intencion="estado_postulaciones",
                    en_alcance=True,
                    texto=(
                        "Tu cuenta es de **Administración/Moderación**, por lo que no registra postulaciones personales. "
                        "Podés consultar métricas y listados institucionales de postulaciones desde **«Reportes personalizados»** (`/admin/reportes`)."
                    ),
                    enlaces=[EnlaceUtilChatbotDTO(texto="Reportes institucionales", ruta="/admin/reportes")],
                )
            return _ResultadoIntencion(
                intencion="estado_postulaciones",
                en_alcance=True,
                texto=(
                    "Todavía no tenés un perfil de egresado completo ni postulaciones registradas en tu cuenta. "
                    "Completá tu perfil en **«Mi Perfil Profesional»** (`/perfil/profesional`) y explorá las ofertas en **«Buscar vacantes»** (`/vacantes`)."
                ),
                enlaces=[
                    EnlaceUtilChatbotDTO(texto="Completar mi perfil", ruta="/perfil/profesional"),
                    EnlaceUtilChatbotDTO(texto="Buscar vacantes", ruta="/vacantes"),
                ],
            )

        # Consulta estrictamente las postulaciones del candidato autenticado (CA2 y CA3)
        apps = (
            self.db.scalars(
                select(Application)
                .options(
                    joinedload(Application.job_posting).joinedload(JobPosting.company),
                    joinedload(Application.current_stage),
                )
                .where(Application.candidate_id == candidato.id)
                .order_by(Application.applied_at.desc())
            )
            .unique()
            .all()
        )

        if not apps:
            return _ResultadoIntencion(
                intencion="estado_postulaciones",
                en_alcance=True,
                texto=(
                    f"Hola {candidato.first_name}, revisé tu cuenta y **actualmente no tenés postulaciones registradas**.\n\n"
                    "Podés explorar las ofertas disponibles para tu universidad en **«Buscar vacantes»** (`/vacantes`) "
                    "o ver las que mejor coinciden con tu perfil en **«Vacantes recomendadas»** (`/recomendaciones`)."
                ),
                enlaces=[
                    EnlaceUtilChatbotDTO(texto="Buscar vacantes", ruta="/vacantes"),
                    EnlaceUtilChatbotDTO(texto="Vacantes recomendadas", ruta="/recomendaciones"),
                ],
            )

        resumen_dtos: list[PostulacionResumenChatbotDTO] = []
        lineas: list[str] = []
        activas = 0

        for app in apps:
            job = app.job_posting
            company: Company | None = job.company if job else None
            titulo_vacante = job.title if job else "Vacante"
            nombre_empresa = (company.trade_name or company.legal_name) if company else "Empresa"
            info_estado = ESTADOS_INFO.get(app.current_status, {"label": app.current_status})
            etiqueta_estado = info_estado["label"]
            etapa_nombre = app.current_stage.name if app.current_stage else None
            fecha_str = app.applied_at.strftime("%d/%m/%Y") if app.applied_at else "—"

            if app.current_status not in ("withdrawn", "rejected"):
                activas += 1

            resumen_dtos.append(
                PostulacionResumenChatbotDTO(
                    application_id=app.id,
                    job_id=app.job_id,
                    job_title=titulo_vacante,
                    company_name=nombre_empresa,
                    current_status=app.current_status,
                    status_label=etiqueta_estado,
                    etapa_actual=etapa_nombre,
                    applied_at=app.applied_at,
                )
            )

            detalle_etapa = f" · Etapa: *{etapa_nombre}*" if etapa_nombre else ""
            lineas.append(
                f"• **{titulo_vacante}** en **{nombre_empresa}** — Estado: **{etiqueta_estado}**{detalle_etapa} (postulado el {fecha_str})."
            )

        # Verificar si tiene entrevistas próximas o propuestas en sus postulaciones
        app_ids = [a.id for a in apps]
        entrevistas = self.db.scalars(
            select(Interview).where(
                Interview.application_id.in_(app_ids),
                Interview.status.in_(("proposed", "confirmed", "rescheduled")),
            )
        ).all()

        encabezado = (
            f"Tenés **{len(apps)} {'postulación registrada' if len(apps) == 1 else 'postulaciones registradas'}** "
            f"en tu cuenta ({activas} {'activa' if activas == 1 else 'activas'}):\n\n"
        )
        cuerpo = "\n".join(lineas[:10])
        if len(lineas) > 10:
            cuerpo += f"\n• ...y {len(lineas) - 10} más en tu historial."

        extra_entrevistas = ""
        if entrevistas:
            extra_entrevistas = (
                f"\n\n📅 Además, tenés **{len(entrevistas)} "
                f"{'entrevista agendada o pendiente de confirmar' if len(entrevistas) == 1 else 'entrevistas agendadas o pendientes de confirmar'}**. "
                "Revisalas desde «Mis postulaciones»."
            )

        return _ResultadoIntencion(
            intencion="estado_postulaciones",
            en_alcance=True,
            texto=encabezado + cuerpo + extra_entrevistas,
            postulaciones=resumen_dtos,
            enlaces=[EnlaceUtilChatbotDTO(texto="Ver Mis postulaciones", ruta="/postulaciones")],
            sugerencias=[
                "¿Qué significa cada estado de postulación?",
                "¿Cómo confirmo una entrevista?",
                "¿Cómo retiro una postulación?",
            ],
        )

    @staticmethod
    def _responder_significado_estados_y_retiro() -> _ResultadoIntencion:
        texto = (
            "En **«Mis postulaciones»** (`/postulaciones`) cada solicitud pasa por los siguientes estados:\n\n"
            "• **Postulado (`applied`):** La empresa recibió tu postulación y aún no la revisó.\n"
            "• **En revisión / Preseleccionado (`in_review`, `shortlisted`):** Tu perfil está siendo evaluado y avanzás en el proceso.\n"
            "• **En entrevista / En pruebas (`interview`, `assessment`):** Estás en etapa de entrevistas o evaluación técnica con la empresa.\n"
            "• **Oferta recibida / Contratado (`offer`, `hired`):** La empresa te seleccionó para el puesto.\n"
            "• **No seleccionado (`rejected`):** El proceso concluyó para esa vacante.\n"
            "• **Postulación retirada (`withdrawn`):** Retiraste tu solicitud.\n\n"
            "**¿Cómo retirar una postulación?** Abrí la postulación en `/postulaciones`, tocá **«Retirar postulación»** e indicá el motivo (podés volver a postularte mientras la oferta siga abierta)."
        )
        return _ResultadoIntencion(
            intencion="significado_estados",
            en_alcance=True,
            texto=texto,
            enlaces=[EnlaceUtilChatbotDTO(texto="Ir a Mis postulaciones", ruta="/postulaciones")],
        )

    def _responder_perfil(self, usuario: CurrentUser) -> _ResultadoIntencion:
        aviso_personalizado = ""
        if self.db is not None and usuario.rol == "candidate":
            candidato = self.db.scalar(
                select(CandidateProfile).where(CandidateProfile.user_id == usuario.id_usuario)
            )
            if candidato is not None:
                perfil_af = motor_afinidad.perfiles_de_candidatos(self.db, {candidato.id})[candidato.id]
                faltantes = perfil_af.faltantes()
                if faltantes:
                    aviso_personalizado = (
                        "\n\n💡 **Sugerencia para tu cuenta actual:** Para mejorar tu afinidad te falta completar:\n"
                        + "\n".join(f"• {f}" for f in faltantes)
                    )
                else:
                    aviso_personalizado = (
                        "\n\n✅ **Tu perfil tiene completas** las secciones clave para el cálculo de afinidad (carrera, habilidades, experiencia e idiomas)."
                    )

        texto = (
            "Tu perfil profesional es tu carta de presentación ante las empresas:\n\n"
            "1. **Completar datos y CV (`/perfil/profesional`):** Cargá tu formación académica (carrera), habilidades con su nivel de dominio, experiencia laboral, idiomas y certificaciones.\n"
            "2. **Configurar privacidad (`/perfil/visibilidad`):** Elegí quién puede ver tu perfil, tu estado de búsqueda laboral y si las empresas pueden ver tus datos de contacto directo."
            + aviso_personalizado
        )
        return _ResultadoIntencion(
            intencion="perfil_cv",
            en_alcance=True,
            texto=texto,
            enlaces=[
                EnlaceUtilChatbotDTO(texto="Mi Perfil Profesional", ruta="/perfil/profesional"),
                EnlaceUtilChatbotDTO(texto="Visibilidad y Privacidad", ruta="/perfil/visibilidad"),
            ],
        )

    @staticmethod
    def _responder_afinidad_recomendaciones() -> _ResultadoIntencion:
        texto = (
            "El **motor de afinidad de EGRESA (HU-23)** compara los requisitos de cada vacante con tu perfil profesional en cuatro criterios ponderados:\n\n"
            "• **Habilidades (40%):** Coincidencia y nivel de dominio en las habilidades técnicas o blandas requeridas.\n"
            "• **Carrera / Formación (30%):** Si tu carrera está entre las solicitadas por la oferta.\n"
            "• **Experiencia laboral (15%):** Años de experiencia acumulados frente al nivel del puesto.\n"
            "• **Idiomas (15%):** Idiomas y nivel requerido.\n\n"
            "🔒 **Transparencia y privacidad:** El cálculo nunca utiliza edad, género, foto, documento ni dirección. En **«Vacantes recomendadas»** (`/recomendaciones`) podés tocar *«¿Por qué?»* en cada oferta para ver qué criterios cumplís y cuáles te faltan."
        )
        return _ResultadoIntencion(
            intencion="afinidad_recomendaciones",
            en_alcance=True,
            texto=texto,
            enlaces=[
                EnlaceUtilChatbotDTO(texto="Ver Vacantes recomendadas", ruta="/recomendaciones"),
                EnlaceUtilChatbotDTO(texto="Completar mi perfil", ruta="/perfil/profesional"),
            ],
        )

    @staticmethod
    def _responder_entrevistas_y_mensajes(usuario: CurrentUser) -> _ResultadoIntencion:
        texto = (
            "**Entrevistas y mensajería en EGRESA:**\n\n"
            "• **Entrevistas (HU-20):** Cuando una empresa te propone una entrevista (presencial o virtual), recibís una notificación y podés **confirmarla** o **solicitar reprogramación** desde el detalle de tu postulación en **«Mis postulaciones»** (`/postulaciones`).\n"
            "• **Mensajería directa (HU-19):** Las empresas y los postulantes pueden comunicarse mediante el chat integrado asociado a cada proceso de selección."
        )
        enlaces = (
            [EnlaceUtilChatbotDTO(texto="Ir a Proceso de Selección", ruta="/seleccion")]
            if usuario.rol == "empresa"
            else [EnlaceUtilChatbotDTO(texto="Ver Mis postulaciones", ruta="/postulaciones")]
        )
        return _ResultadoIntencion(
            intencion="entrevistas_mensajes",
            en_alcance=True,
            texto=texto,
            enlaces=enlaces,
        )

    @staticmethod
    def _responder_notificaciones() -> _ResultadoIntencion:
        texto = (
            "**Notificaciones y alertas (HU-21):**\n\n"
            "1. **Campana de avisos:** En la barra superior ves las notificaciones de cambios de etapa en tus postulaciones, entrevistas propuestas, mensajes nuevos y vacantes con alta afinidad (60% o más).\n"
            "2. **Preferencias (`/notificaciones`):** Podés elegir qué tipos de avisos querés recibir (etapas, entrevistas, mensajes, ofertas) y por qué canal (en la app, correo o push).\n"
            "3. **Avisos Push:** Desde el panel de notificaciones podés tocar *«Activar en este navegador»* para recibir alertas en tiempo real aunque no tengas EGRESA abierto."
        )
        return _ResultadoIntencion(
            intencion="notificaciones_push",
            en_alcance=True,
            texto=texto,
            enlaces=[EnlaceUtilChatbotDTO(texto="Panel de notificaciones", ruta="/notificaciones")],
        )

    @staticmethod
    def _responder_denuncias() -> _ResultadoIntencion:
        texto = (
            "**Denuncia de ofertas sospechosas (HU-22):**\n\n"
            "1. Si detectás una vacante con información falsa, discriminatoria o fraudulenta, abrila y hacé clic en **«Denunciar oferta»**.\n"
            "2. Elegí el motivo y describí el problema.\n"
            "3. **Protección automática:** Cuando una oferta acumula **3 denuncias fundamentadas**, el sistema la oculta preventivamente hasta que un moderador de la universidad revise el caso y tome una decisión."
        )
        return _ResultadoIntencion(
            intencion="denunciar_oferta",
            en_alcance=True,
            texto=texto,
            enlaces=[EnlaceUtilChatbotDTO(texto="Explorar vacantes", ruta="/vacantes")],
        )

    @staticmethod
    def _responder_validacion() -> _ResultadoIntencion:
        texto = (
            "**Validación institucional en EGRESA:**\n\n"
            "• **Egresados:** Al registrarte, tu universidad verifica que seas egresado o estudiante habilitado. Mientras tu cuenta dice *«pendiente de validación»* podés ir completando tu perfil profesional; una vez validada, ya podés postularte a vacantes.\n"
            "• **Empresas:** Cada empresa se registra y solicita autorización en las universidades donde desea reclutar talento (`/dashboard`)."
        )
        return _ResultadoIntencion(
            intencion="validacion_cuenta",
            en_alcance=True,
            texto=texto,
            enlaces=[EnlaceUtilChatbotDTO(texto="Ir a mi Panel", ruta="/dashboard")],
        )

    @staticmethod
    def _responder_empresa_vacantes_seleccion() -> _ResultadoIntencion:
        texto = (
            "**Gestión de vacantes y selección para Empresas:**\n\n"
            "1. **Publicar vacante (`/vacantes/crear`):** Completá el título, modalidad, habilidades ponderadas y preguntas de filtro (incluyendo preguntas excluyentes o *knockout*). La oferta pasa a revisión institucional antes de publicarse.\n"
            "2. **Mis vacantes (`/vacantes/mis-vacantes`):** Pausá, reactivá, editá preguntas de filtro o cerrá tus convocatorias.\n"
            "3. **Proceso de selección (`/seleccion`):** Usá el tablero por etapas para avanzar o descartar postulantes, registrar notas internas, agendar entrevistas y comparar hasta 3 candidatos lado a lado.\n"
            "4. **Sugerencias con IA (`/empresa/sugerencias-ia`):** Consultá el ranking de candidatos ordenados por porcentaje de afinidad con explicación detallada."
        )
        return _ResultadoIntencion(
            intencion="empresa_vacantes_seleccion",
            en_alcance=True,
            texto=texto,
            enlaces=[
                EnlaceUtilChatbotDTO(texto="Publicar vacante", ruta="/vacantes/crear"),
                EnlaceUtilChatbotDTO(texto="Proceso de selección", ruta="/seleccion"),
                EnlaceUtilChatbotDTO(texto="Sugerencias IA", ruta="/empresa/sugerencias-ia"),
            ],
        )

    @staticmethod
    def _responder_reportes() -> _ResultadoIntencion:
        texto = (
            "**Reportes personalizados:**\n\n"
            "1. Ingresá a **«Reportes»** (`/reportes` para empresas o `/admin/reportes` para universidades).\n"
            "2. Elegí la fuente de datos (egresados, empresas, vacantes o postulaciones) y aplicá los filtros que necesites.\n"
            "3. Seleccioná y ordená las columnas a mostrar.\n"
            "4. Generá la vista previa y exportá el reporte en formato **Excel (`.xlsx`), PDF o HTML**, o envialo por correo."
        )
        return _ResultadoIntencion(
            intencion="reportes",
            en_alcance=True,
            texto=texto,
            enlaces=[EnlaceUtilChatbotDTO(texto="Ir a Reportes", ruta="/reportes")],
        )

    @staticmethod
    def _responder_administracion() -> _ResultadoIntencion:
        texto = (
            "**Módulos de Administración Universitaria y SaaS (`/admin`):**\n\n"
            "• **Validación y Moderación:** Aprobá cuentas de egresados (`/admin/validacion-egresados`), autorizá empresas (`/admin/empresas`), moderá vacantes (`/admin/moderacion-vacantes`) y resolvé denuncias (`/admin/denuncias`).\n"
            "• **Grupos y permisos (`/admin/grupos`):** Definí qué menús y acciones puede usar cada grupo de administradores o moderadores.\n"
            "• **Bitácora confidencial (`/admin/bitacora`):** Auditoría cifrada de acciones; requiere la clave de desarrollador para descifrar las entradas.\n"
            "• **Copias de seguridad (`/admin/respaldos`) y Tareas (`/admin/tareas`):** Creación manual/automática de backups, verificación y restauración segura."
        )
        return _ResultadoIntencion(
            intencion="administracion",
            en_alcance=True,
            texto=texto,
            enlaces=[EnlaceUtilChatbotDTO(texto="Panel de Administración", ruta="/admin")],
        )

    @staticmethod
    def _responder_cuenta_seguridad() -> _ResultadoIntencion:
        texto = (
            "**Seguridad de tu cuenta y contraseña:**\n\n"
            "• **Cambiar contraseña (`/cuenta/contrasena`):** Ingresá tu contraseña actual y la nueva (mínimo 8 caracteres). Si tu cuenta fue creada con clave temporal, el sistema te pedirá cambiarla al primer ingreso.\n"
            "• **Bloqueo temporal:** Tras varios intentos fallidos de inicio de sesión, la cuenta se protege bloqueándose por unos minutos.\n"
            "• **Cierre por inactividad:** Por seguridad, la sesión se cierra automáticamente si no hay actividad durante un tiempo prolongado."
        )
        return _ResultadoIntencion(
            intencion="cuenta_seguridad",
            en_alcance=True,
            texto=texto,
            enlaces=[EnlaceUtilChatbotDTO(texto="Cambiar contraseña", ruta="/cuenta/contrasena")],
        )

    @staticmethod
    def _responder_buscar_vacantes() -> _ResultadoIntencion:
        texto = (
            "En **«Buscar vacantes»** (`/vacantes`) podés explorar todas las ofertas laborales vigentes de empresas habilitadas por tu universidad:\n\n"
            "• Filtrá por palabra clave, área, ciudad, modalidad (presencial, remoto, híbrido) o nivel de experiencia.\n"
            "• Con tu sesión de egresado iniciada, cada oferta muestra tu **porcentaje de afinidad**.\n"
            "• También podés ir a **«Vacantes recomendadas»** (`/recomendaciones`) para ver las ofertas ordenadas de mayor a menor afinidad con tu perfil."
        )
        return _ResultadoIntencion(
            intencion="buscar_vacantes",
            en_alcance=True,
            texto=texto,
            enlaces=[
                EnlaceUtilChatbotDTO(texto="Buscar vacantes", ruta="/vacantes"),
                EnlaceUtilChatbotDTO(texto="Vacantes recomendadas", ruta="/recomendaciones"),
            ],
        )
