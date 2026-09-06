from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.candidato import CandidateProfile
from app.models.postulacion import Application, ApplicationAnswer
from app.models.vacante import JobPosting, ScreeningQuestion
from app.models.empresa import Company
from .schema import PostulacionCreate, PostulacionResponse, PostulacionListResponse
from typing import List

class PostulacionService:
    def postular_vacante(self, db: Session, user_id: str, data: PostulacionCreate) -> PostulacionResponse:
        # 1. Obtener perfil del candidato (se asume que el user_id es el id en app_user)
        # La tabla application requiere candidate_id (que es CandidateProfile.id)
        candidate = db.query(CandidateProfile).filter(CandidateProfile.user_id == user_id).first()
        if not candidate:
            raise HTTPException(status_code=403, detail="Perfil de candidato no encontrado.")

        # Verificar validación
        if candidate.verification_status != "verified" and candidate.verification_status != "approved":
            # Nota: Según reglas, solo validado puede postularse.
            # raise HTTPException(status_code=403, detail="Tu perfil debe estar validado para postularte a vacantes.")
            pass # Relaxed for testing if needed, but per rule we should enforce it. Let's strictly enforce:
            
            if candidate.verification_status != "verified":
                 raise HTTPException(status_code=403, detail="Solo un egresado validado puede postularse.")

        # 2. Verificar existencia de la vacante
        vacante = db.query(JobPosting).filter(JobPosting.id == data.job_id).first()
        if not vacante:
            raise HTTPException(status_code=404, detail="La vacante no existe.")
        
        # 3. Verificar que no exista postulación previa
        existing_app = db.query(Application).filter(
            Application.candidate_id == candidate.id,
            Application.job_id == data.job_id
        ).first()
        
        if existing_app:
            raise HTTPException(status_code=400, detail="Ya te has postulado a esta vacante.")

        # 4. Verificar respuestas a preguntas de filtro requeridas
        required_questions = db.query(ScreeningQuestion).filter(
            ScreeningQuestion.job_posting_id == data.job_id,
            ScreeningQuestion.is_required == True
        ).all()
        
        required_q_ids = {str(q.id) for q in required_questions}
        provided_q_ids = {str(ans.question_id) for ans in data.answers}
        
        missing_q_ids = required_q_ids - provided_q_ids
        if missing_q_ids:
            raise HTTPException(status_code=400, detail="Faltan respuestas a preguntas requeridas de la vacante.")

        # 5. Crear la postulación
        new_app = Application(
            candidate_id=candidate.id,
            job_id=data.job_id,
            current_status="applied"
        )
        db.add(new_app)
        db.flush() # Para obtener el ID

        # 6. Guardar respuestas
        for ans in data.answers:
            new_ans = ApplicationAnswer(
                application_id=new_app.id,
                question_id=ans.question_id,
                selected_option_id=ans.selected_option_id,
                answer_text=ans.answer_text,
                answer_number=ans.answer_number
            )
            db.add(new_ans)

        db.commit()
        db.refresh(new_app)

        return PostulacionResponse(
            id=new_app.id,
            job_id=new_app.job_id,
            current_status=new_app.current_status,
            message="Postulación exitosa"
        )

    def obtener_mis_postulaciones(self, db: Session, user_id: str) -> List[PostulacionListResponse]:
        candidate = db.query(CandidateProfile).filter(CandidateProfile.user_id == user_id).first()
        if not candidate:
            return []

        results = (
            db.query(Application, JobPosting, Company)
            .join(JobPosting, Application.job_id == JobPosting.id)
            .join(Company, JobPosting.company_id == Company.id)
            .filter(Application.candidate_id == candidate.id)
            .order_by(Application.applied_at.desc())
            .all()
        )

        lista = []
        for app, job, comp in results:
            lista.append(PostulacionListResponse(
                id=app.id,
                job_id=job.id,
                job_title=job.title,
                company_name=comp.legal_name,
                current_status=app.current_status,
                applied_at=app.applied_at
            ))
        return lista
