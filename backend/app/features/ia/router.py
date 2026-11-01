"""Módulos 5.1.11 a 5.1.14 — IA: recomendación de vacantes (HU-23), sugerencia de candidatos (HU-24),
búsqueda semántica (HU-25), asistente generativo (HU-26, HU-27) y chatbot de orientación (HU-28)."""

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.common.request_context import get_client_ip
from app.core.database import get_db
from app.features.ia.schema import (
    BusquedaSemanticaResponse,
    ChatbotConsultaRequest,
    ChatbotRespuestaResponse,
    ChatbotSesionResponse,
    GenerarBorradorVacanteRequest,
    GenerarBorradorVacanteResponse,
    GenerarResumenRequest,
    GenerarResumenResponse,
    RecomendacionesResponse,
    SugerenciasCandidatosResponse,
    VacanteRecomendadaResponse,
)
from app.features.ia.services.afinidad import ia_activa
from app.features.ia.services.asistente_generativo_service import AsistenteGenerativoService
from app.features.ia.services.candidato_sugerencia_service import CandidatoSugerenciaService
from app.features.ia.services.chatbot_service import ChatbotService, chatbot_activo
from app.features.ia.services.recomendacion_service import RecomendacionService
from app.features.ia.services.semantic_search_service import SemanticSearchService
from app.security.dependencies import CurrentUser, get_current_user, get_current_user_optional, require_roles

router = APIRouter(prefix="/ia", tags=["inteligencia-artificial"])
ai_router = APIRouter(prefix="/ai", tags=["inteligencia-artificial"])

_solo_egresado = require_roles("candidate")
# Igual que el pipeline de selección: además del rol, el servicio exige ser
# miembro de la empresa dueña de la vacante o admin de plataforma.
_solo_empresa_o_admin = require_roles("empresa", "platform_admin")


@router.get("/_status")
def estado_modulo() -> dict:
    return {
        "modulo": "inteligencia_artificial",
        "recomendaciones": "activo" if ia_activa() else "apagado",
        "chatbot": "activo" if chatbot_activo() else "apagado",
    }


# --- HU-27: REDACCIÓN ASISTIDA DE VACANTE CON IA (EMPRESA) ---
@router.post("/job-description", response_model=GenerarBorradorVacanteResponse)
@router.post("/borrador-vacante", response_model=GenerarBorradorVacanteResponse)
def generar_borrador_vacante(
    payload: GenerarBorradorVacanteRequest,
    request: Request,
    current_user: CurrentUser = Depends(_solo_empresa_o_admin),
    db: Session = Depends(get_db),
):
    """HU-27: Genera un borrador estructurado de vacante (descripción, requisitos y beneficios) con IA."""
    return AsistenteGenerativoService(db).generar_borrador_vacante(
        indicacion=payload.indicacion,
        cargo=payload.cargo,
        modalidad=payload.modalidad,
        requisitos_clave=payload.requisitos_clave,
        variante=payload.variante,
        usuario_id=current_user.id_usuario,
        ip_address=get_client_ip(request),
    )


@ai_router.post("/job-description", response_model=GenerarBorradorVacanteResponse)
def generar_borrador_vacante_ai(
    payload: GenerarBorradorVacanteRequest,
    request: Request,
    current_user: CurrentUser = Depends(_solo_empresa_o_admin),
    db: Session = Depends(get_db),
):
    """HU-27: Alias bajo /api/ai/job-description."""
    return generar_borrador_vacante(payload, request, current_user, db)


# --- HU-25: BÚSQUEDA SEMÁNTICA DE VACANTES ---
@router.get("/busqueda-semantica", response_model=BusquedaSemanticaResponse)
def buscar_semantico_ia(
    q: str = Query(..., min_length=1, max_length=500, description="Consulta en lenguaje natural"),
    ciudad: str | None = Query(default=None, max_length=100),
    modalidad: str | None = Query(default=None),
    carrera_id: uuid.UUID | None = Query(default=None),
    salario_min: Decimal | None = Query(default=None, ge=0),
    seniority: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """HU-25: Búsqueda Semántica de Vacantes (alias bajo /ia)."""
    return SemanticSearchService(db).buscar(
        q=q,
        ciudad=ciudad,
        modalidad=modalidad,
        carrera_id=carrera_id,
        salario_min=salario_min,
        seniority=seniority,
        page=page,
        page_size=page_size,
    )


# --- HU-26: ASISTENTE GENERATIVO DE RESUMEN PROFESIONAL (EGRESADO) ---
@router.post("/resumen-profesional/generar", response_model=GenerarResumenResponse)
def generar_resumen_profesional(
    payload: GenerarResumenRequest | None = None,
    current_user: CurrentUser = Depends(_solo_egresado),
    db: Session = Depends(get_db),
):
    """HU-26: Genera un borrador de resumen profesional con IA a partir de los datos cargados en el perfil."""
    variante = payload.variante if payload else 1
    enfoque = payload.enfoque if payload else "general"
    return AsistenteGenerativoService(db).generar_resumen_profesional(
        usuario_id=current_user.id_usuario,
        variante=variante,
        enfoque=enfoque,
    )


# --- HU-23: RECOMENDACIÓN DE VACANTES PARA EGRESADOS ---
@router.get("/recomendaciones", response_model=RecomendacionesResponse)
def vacantes_recomendadas(current_user: CurrentUser = Depends(_solo_egresado), db: Session = Depends(get_db)):
    """HU-23: vacantes vigentes ordenadas por afinidad con el perfil del egresado."""
    return RecomendacionService(db).vacantes_recomendadas(current_user.id_usuario)


@router.get("/recomendaciones/{vacante_id}", response_model=VacanteRecomendadaResponse)
def detalle_recomendacion(
    vacante_id: uuid.UUID, current_user: CurrentUser = Depends(_solo_egresado), db: Session = Depends(get_db)
):
    """HU-23 (CP02): criterios que el egresado cumple y que le faltan para una vacante."""
    return RecomendacionService(db).detalle(current_user.id_usuario, vacante_id)


# --- HU-24: SUGERENCIA DE CANDIDATOS POR AFINIDAD PARA EMPRESAS ---
@router.get("/sugerencias-candidatos/{vacante_id}", response_model=SugerenciasCandidatosResponse)
def sugerir_candidatos_vacante(
    vacante_id: uuid.UUID,
    umbral_minimo: int = Query(0, ge=0, le=100, description="Porcentaje mínimo de afinidad (ej. 70)"),
    current_user: CurrentUser = Depends(_solo_empresa_o_admin),
    db: Session = Depends(get_db),
):
    """HU-24: Ranking inteligente de candidatos sugeridos para una vacante con explicabilidad de coincidencia."""
    return CandidatoSugerenciaService(db).sugerir_candidatos_para_vacante(
        vacante_id=vacante_id,
        user_id=current_user.id_usuario,
        umbral_minimo=umbral_minimo,
    )


# --- HU-28: CHATBOT DE ORIENTACIÓN ---
@router.get("/chatbot/sesion", response_model=ChatbotSesionResponse)
def abrir_sesion_chatbot(
    session_id: uuid.UUID | None = Query(default=None, description="ID de sesión existente"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """HU-28: Abre el chatbot para cualquier usuario autenticado y recupera su sesión activa (o informa 503 si no está disponible, CP04)."""
    return ChatbotService(db).abrir_sesion(current_user, session_id=session_id)


@router.post("/chatbot/nueva-sesion", response_model=ChatbotSesionResponse)
def nueva_sesion_chatbot(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """HU-28: Cierra la conversación anterior y comienza una nueva sesión del chatbot."""
    return ChatbotService(db).abrir_sesion(current_user, nueva=True)


@router.post("/chatbot/mensajes", response_model=ChatbotRespuestaResponse)
@router.post("/chatbot", response_model=ChatbotRespuestaResponse)
def consultar_chatbot(
    data: ChatbotConsultaRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """HU-28: Envía una consulta en lenguaje natural al chatbot y registra toda la interacción."""
    return ChatbotService(db).consultar(current_user, data)
