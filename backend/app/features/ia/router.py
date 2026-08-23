"""Módulos 5.1.11 a 5.1.14 — IA: recomendación, asistente generativo, chatbot, análisis predictivo.
Implementación prevista en Sprints 3 y 4."""

from fastapi import APIRouter

router = APIRouter(prefix="/ia", tags=["inteligencia-artificial"])


@router.get("/_status")
def estado_modulo() -> dict:
    return {"modulo": "inteligencia_artificial", "sprint_previsto": "3-4"}
