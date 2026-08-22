"""Módulo 5.1.6 — Proceso de selección. Implementación prevista en Sprint 2."""

from fastapi import APIRouter

router = APIRouter(prefix="/seleccion", tags=["proceso-seleccion"])


@router.get("/_status")
def estado_modulo() -> dict:
    return {"modulo": "proceso_seleccion", "sprint_previsto": 2}
