"""Módulo 5.1.7 — Comunicación y entrevistas. Implementación prevista en Sprint 2."""

from fastapi import APIRouter

router = APIRouter(prefix="/comunicacion", tags=["comunicacion"])


@router.get("/_status")
def estado_modulo() -> dict:
    return {"modulo": "comunicacion_y_entrevistas", "sprint_previsto": 2}
