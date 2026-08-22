"""Módulo 5.1.10 — Reportes institucionales. Implementación prevista en Sprint 3."""

from fastapi import APIRouter

router = APIRouter(prefix="/reportes", tags=["reportes-institucionales"])


@router.get("/_status")
def estado_modulo() -> dict:
    return {"modulo": "reportes_institucionales", "sprint_previsto": 3}
