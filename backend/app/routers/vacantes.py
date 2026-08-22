"""Módulo 5.1.4 — Gestión de vacantes. Implementación prevista en Sprint 1."""

from fastapi import APIRouter

router = APIRouter(prefix="/vacantes", tags=["vacantes"])


@router.get("/_status")
def estado_modulo() -> dict:
    return {"modulo": "gestion_vacantes", "sprint_previsto": 1}
