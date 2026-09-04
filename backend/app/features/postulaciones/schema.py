from pydantic import BaseModel
from typing import List, Optional
import uuid
from datetime import datetime

class ApplicationAnswerCreate(BaseModel):
    question_id: uuid.UUID
    selected_option_id: Optional[uuid.UUID] = None
    answer_text: Optional[str] = None
    answer_number: Optional[float] = None

class PostulacionCreate(BaseModel):
    job_id: uuid.UUID
    answers: Optional[List[ApplicationAnswerCreate]] = []

class PostulacionResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    current_status: str
    message: str

class PostulacionListResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    job_title: str
    company_name: str
    current_status: str
    applied_at: datetime
