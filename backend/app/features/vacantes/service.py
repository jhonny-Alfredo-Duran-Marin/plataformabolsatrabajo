import uuid
from decimal import Decimal
from sqlalchemy.orm import Session

from app.common.exceptions import NotFoundException
from app.features.vacantes.repository import VacanteRepository
from app.features.vacantes.schema import (
    CarreraEnVacanteResponse,
    EmpresaEnVacanteResponse,
    FiltrosDisponiblesResponse,
    HabilidadEnVacanteResponse,
    VacanteDetalleResponse,
    VacanteResumenResponse,
    VacantesPaginadasResponse,
)
from app.models.candidato import CandidateEducation, CandidateProfile, CandidateSkill
from app.models.oferta import JobPosting


class VacanteService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = VacanteRepository(db)

    def buscar_vacantes(
        self,
        q: str | None = None,
        carrera_id: uuid.UUID | None = None,
        categoria_id: uuid.UUID | None = None,
        ciudad: str | None = None,
        modalidad: str | None = None,
        jornada: str | None = None,
        seniority: str | None = None,
        salario_min: Decimal | None = None,
        salario_max: Decimal | None = None,
        ordenar_por: str = "fecha",
        limit: int = 20,
        offset: int = 0,
        usuario_id: uuid.UUID | None = None,
    ) -> VacantesPaginadasResponse:
        """Busca vacantes con filtros combinados y calcula la afinidad con el perfil del egresado si está autenticado."""
        items, total = self.repo.buscar_vacantes(
            q=q,
            carrera_id=carrera_id,
            categoria_id=categoria_id,
            ciudad=ciudad,
            modalidad=modalidad,
            jornada=jornada,
            seniority=seniority,
            salario_min=salario_min,
            salario_max=salario_max,
            solo_vigentes=True,
            ordenar_por=ordenar_por if ordenar_por != "afinidad" else "fecha",
            limit=limit,
            offset=offset,
        )

        # Obtener perfil y datos del candidato para cálculo de afinidad
        candidato_skills: set[uuid.UUID] = set()
        candidato_carreras: set[uuid.UUID] = set()
        es_candidato = False

        if usuario_id:
            perfil = (
                self.db.query(CandidateProfile)
                .filter(CandidateProfile.user_id == usuario_id)
                .one_or_none()
            )
            if perfil:
                es_candidato = True
                candidato_skills = {
                    cs.skill_id
                    for cs in self.db.query(CandidateSkill).filter(CandidateSkill.candidate_id == perfil.id).all()
                }
                candidato_carreras = {
                    ce.field_of_study_id
                    for ce in self.db.query(CandidateEducation)
                    .filter(CandidateEducation.candidate_id == perfil.id, CandidateEducation.field_of_study_id.isnot(None))
                    .all()
                    if ce.field_of_study_id is not None
                }

        vacantes_dto: list[VacanteResumenResponse] = []
        for vacante in items:
            afinidad = None
            if es_candidato:
                afinidad = self._calcular_afinidad(vacante, candidato_skills, candidato_carreras)

            dto = self._mapear_a_resumen(vacante, afinidad)
            vacantes_dto.append(dto)

        # Si el usuario solicitó ordenar por afinidad y está autenticado
        if ordenar_por == "afinidad" and es_candidato:
            vacantes_dto.sort(key=lambda x: (x.afinidad_porcentaje or 0), reverse=True)

        return VacantesPaginadasResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=vacantes_dto,
        )

    def obtener_detalle(
        self,
        vacante_id: uuid.UUID,
        usuario_id: uuid.UUID | None = None,
    ) -> VacanteDetalleResponse:
        """Obtiene el detalle completo de una vacante e incrementa sus vistas."""
        vacante = self.repo.obtener_por_id(vacante_id)
        if not vacante:
            raise NotFoundException("La vacante solicitada no existe o no está disponible.")

        # Incrementar contador de vistas de forma asíncrona / atómica
        self.repo.incrementar_vistas(vacante_id)

        afinidad = None
        if usuario_id:
            perfil = (
                self.db.query(CandidateProfile)
                .filter(CandidateProfile.user_id == usuario_id)
                .one_or_none()
            )
            if perfil:
                candidato_skills = {
                    cs.skill_id
                    for cs in self.db.query(CandidateSkill).filter(CandidateSkill.candidate_id == perfil.id).all()
                }
                candidato_carreras = {
                    ce.field_of_study_id
                    for ce in self.db.query(CandidateEducation)
                    .filter(CandidateEducation.candidate_id == perfil.id, CandidateEducation.field_of_study_id.isnot(None))
                    .all()
                    if ce.field_of_study_id is not None
                }
                afinidad = self._calcular_afinidad(vacante, candidato_skills, candidato_carreras)

        resumen = self._mapear_a_resumen(vacante, afinidad)

        responsabilidades = (
            vacante.responsibilities_json
            if isinstance(vacante.responsibilities_json, list)
            else []
        )
        requisitos = (
            vacante.requirements_json
            if isinstance(vacante.requirements_json, list)
            else []
        )
        beneficios = (
            vacante.benefits_json
            if isinstance(vacante.benefits_json, list)
            else []
        )

        empresa = vacante.company
        return VacanteDetalleResponse(
            **resumen.model_dump(),
            responsibilities=responsabilidades,
            requirements=requisitos,
            benefits=beneficios,
            company_contact_email=empresa.contact_email if empresa else None,
            company_phone=empresa.phone if empresa else None,
            company_address=empresa.address if empresa else None,
        )

    def obtener_filtros_disponibles(self) -> FiltrosDisponiblesResponse:
        """Obtiene las opciones disponibles para los filtros de búsqueda."""
        data = self.repo.obtener_filtros_disponibles()
        return FiltrosDisponiblesResponse(**data)

    def _calcular_afinidad(
        self,
        vacante: JobPosting,
        candidato_skills: set[uuid.UUID],
        candidato_carreras: set[uuid.UUID],
    ) -> int:
        """Calcula el porcentaje de afinidad (0-100%) entre el candidato y la vacante."""
        score = 0
        total_peso = 0

        # Coincidencia de carrera (40 puntos máximos)
        carreras_vacante = {ep.field_of_study_id for ep in vacante.education_preferences}
        if carreras_vacante:
            total_peso += 40
            if candidato_carreras & carreras_vacante:
                score += 40
        else:
            # Si la vacante no exige una carrera específica, aporta puntaje base
            score += 20
            total_peso += 20

        # Coincidencia de habilidades (60 puntos máximos)
        skills_vacante = {js.skill_id for js in vacante.skills}
        if skills_vacante:
            total_peso += 60
            coincidencias = len(candidato_skills & skills_vacante)
            fraccion = coincidencias / len(skills_vacante)
            score += int(fraccion * 60)
        else:
            score += 30
            total_peso += 30

        if total_peso == 0:
            return 50

        porcentaje = int((score / total_peso) * 100)
        return max(15, min(98, porcentaje))

    def _mapear_a_resumen(
        self,
        vacante: JobPosting,
        afinidad: int | None = None,
    ) -> VacanteResumenResponse:
        empresa = vacante.company
        empresa_dto = EmpresaEnVacanteResponse(
            id=empresa.id,
            legal_name=empresa.legal_name,
            trade_name=empresa.trade_name,
            city=empresa.city,
            sector_name=empresa.sector.name if empresa.sector else None,
            website=empresa.website,
            description=empresa.description,
        )

        skills_dto = [
            HabilidadEnVacanteResponse(
                skill_id=js.skill_id,
                name=js.skill.name if js.skill else "",
                importance=js.importance,
                min_proficiency=js.min_proficiency,
            )
            for js in vacante.skills
            if js.skill
        ]

        carreras_dto = [
            CarreraEnVacanteResponse(
                field_of_study_id=ep.field_of_study_id,
                name=ep.field_of_study.name if ep.field_of_study else "",
                education_level=ep.education_level,
                is_required=ep.is_required,
            )
            for ep in vacante.education_preferences
            if ep.field_of_study
        ]

        return VacanteResumenResponse(
            id=vacante.id,
            company=empresa_dto,
            category_id=vacante.category_id,
            category_name=vacante.category.name if vacante.category else None,
            title=vacante.title,
            description=vacante.description,
            seniority_level=vacante.seniority_level,
            employment_type=vacante.employment_type,
            work_modality=vacante.work_modality,
            country_code=vacante.country_code,
            city=vacante.city,
            salary_min=vacante.salary_min if vacante.salary_visible else None,
            salary_max=vacante.salary_max if vacante.salary_visible else None,
            currency=vacante.currency if vacante.salary_visible else None,
            salary_visible=vacante.salary_visible,
            positions_available=vacante.positions_available,
            status=vacante.status,
            min_education_level=vacante.min_education_level,
            min_years_experience=vacante.min_years_experience,
            application_deadline=vacante.application_deadline,
            published_at=vacante.published_at,
            view_count=vacante.view_count,
            skills=skills_dto,
            education_preferences=carreras_dto,
            afinidad_porcentaje=afinidad,
        )

