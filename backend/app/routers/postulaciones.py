"""Módulo 5.1.5 — Postulación y seguimiento. Implementación prevista en Sprint 1."""

from fastapi import APIRouter

router = APIRouter(prefix="/postulaciones", tags=["postulaciones"])


@router.get("/_status")
def estado_modulo() -> dict:
    return {"modulo": "postulacion_y_seguimiento", "sprint_previsto": 1}
