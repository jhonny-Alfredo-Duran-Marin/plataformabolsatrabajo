"""Módulo 5.1.5 — Postulación y seguimiento. Implementación prevista en Sprint 1."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.security.dependencies import get_current_user, CurrentUser
from .schema import PostulacionCreate, PostulacionResponse, PostulacionListResponse
from .service import PostulacionService
from typing import List

router = APIRouter(prefix="/postulaciones", tags=["postulaciones"])

@router.get("/_status")
def estado_modulo() -> dict:
    return {"modulo": "postulacion_y_seguimiento", "sprint_previsto": 1}

@router.get("/", response_model=List[PostulacionListResponse])
def obtener_mis_postulaciones(db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    user_id = str(current_user.id_usuario)
    service = PostulacionService()
    return service.obtener_mis_postulaciones(db, user_id)

@router.post("/", response_model=PostulacionResponse)
def postular_a_vacante(data: PostulacionCreate, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    user_id = str(current_user.id_usuario)
    service = PostulacionService()
    return service.postular_vacante(db, user_id, data)
