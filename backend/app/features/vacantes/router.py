"""Módulo 5.1.4 — Gestión de vacantes. Implementación prevista en Sprint 1."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.vacante import ScreeningQuestion, ScreeningOption
from typing import List, Optional
from pydantic import BaseModel
import uuid

router = APIRouter(prefix="/vacantes", tags=["vacantes"])

class ScreeningOptionSchema(BaseModel):
    id: uuid.UUID
    option_text: str
    
class ScreeningQuestionSchema(BaseModel):
    id: uuid.UUID
    question_text: str
    question_type: str
    is_required: bool
    options: List[ScreeningOptionSchema] = []

    class Config:
        from_attributes = True

@router.get("/_status")
def estado_modulo() -> dict:
    return {"modulo": "gestion_vacantes", "sprint_previsto": 1}

@router.get("/{id}/preguntas", response_model=List[ScreeningQuestionSchema])
def obtener_preguntas_vacante(id: uuid.UUID, db: Session = Depends(get_db)):
    questions = db.query(ScreeningQuestion).filter(ScreeningQuestion.job_posting_id == id).order_by(ScreeningQuestion.position).all()
    
    # Normally we would use relationship() in the model, but since we didn't add it, we query manually or add relationship
    result = []
    for q in questions:
        options = db.query(ScreeningOption).filter(ScreeningOption.question_id == q.id).order_by(ScreeningOption.position).all()
        q_dict = {
            "id": q.id,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "is_required": q.is_required,
            "options": [{"id": o.id, "option_text": o.option_text} for o in options]
        }
        result.append(q_dict)
    return result
