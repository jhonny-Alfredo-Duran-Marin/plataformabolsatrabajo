"""Módulo 5.1.8 — Notificaciones y alertas. Implementación prevista en Sprint 2."""

from fastapi import APIRouter

router = APIRouter(prefix="/notificaciones", tags=["notificaciones"])


@router.get("/_status")
def estado_modulo() -> dict:
    return {"modulo": "notificaciones_y_alertas", "sprint_previsto": 2}
