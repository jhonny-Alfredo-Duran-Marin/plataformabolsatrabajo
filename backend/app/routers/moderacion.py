"""Módulo 5.1.9 — Moderación y antifraude. Implementación prevista en Sprint 3."""

from fastapi import APIRouter

router = APIRouter(prefix="/moderacion", tags=["moderacion"])


@router.get("/_status")
def estado_modulo() -> dict:
    return {"modulo": "moderacion_y_antifraude", "sprint_previsto": 3}
