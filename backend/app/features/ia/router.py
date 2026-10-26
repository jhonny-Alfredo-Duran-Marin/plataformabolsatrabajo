"""Módulos 5.1.11 a 5.1.14 — IA: recomendación de vacantes (HU-23), sugerencia de candidatos (HU-24) y asistente generativo (HU-26)."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.features.ia.schema import (
    GenerarResumenRequest,
    GenerarResumenResponse,
    RecomendacionesResponse,
    SugerenciasCandidatosResponse,
    VacanteRecomendadaResponse,
)
from app.features.ia.services.afinidad import ia_activa
from app.features.ia.services.asistente_generativo_service import AsistenteGenerativoService
from app.features.ia.services.candidato_sugerencia_service import CandidatoSugerenciaService
from app.features.ia.services.recomendacion_service import RecomendacionService
from app.security.dependencies import CurrentUser, get_current_user, require_roles

router = APIRouter(prefix="/ia", tags=["inteligencia-artificial"])

_solo_egresado = require_roles("candidate")
# Igual que el pipeline de selección: además del rol, el servicio exige ser
# miembro de la empresa dueña de la vacante.
_solo_empresa_o_admin = require_roles("empresa", "platform_admin")


@router.get("/_status")
def estado_modulo() -> dict:
    return {"modulo": "inteligencia_artificial", "recomendaciones": "activo" if ia_activa() else "apagado"}


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
