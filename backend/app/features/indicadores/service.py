"""Servicio de cálculo y agregación para el Tablero de Indicadores de Inserción Laboral (HU-31)."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.candidato import CandidateEducation, CandidateProfile, CandidateSkill
from app.models.catalogo import FieldOfStudy, Skill
from app.models.colocacion import Placement
from app.models.encuesta import Survey, SurveyAnswer, SurveyQuestion, SurveyResponse
from app.security.tenant import AlcanceStaff
from app.features.indicadores.schema import (
    HabilidadDemandaItem,
    IndicadoresFiltrosOpciones,
    IndicadoresResponse,
)


class IndicadoresService:
    def __init__(self, db: Session):
        self.db = db

    def obtener_filtros_disponibles(self, alcance: AlcanceStaff) -> IndicadoresFiltrosOpciones:
        """Obtiene las carreras con egresados/colocaciones y los períodos disponibles para filtrar."""
        institution_id = alcance.institution_id

        # Carreras de la institución
        q_carreras = (
            select(FieldOfStudy.id, FieldOfStudy.name)
            .join(CandidateEducation, CandidateEducation.field_of_study_id == FieldOfStudy.id)
            .join(CandidateProfile, CandidateProfile.id == CandidateEducation.candidate_id)
            .distinct()
            .order_by(FieldOfStudy.name)
        )
        if institution_id:
            q_carreras = q_carreras.where(CandidateProfile.institution_id == institution_id)

        carreras_rows = self.db.execute(q_carreras).all()
        carreras_list = [{"id": str(r.id), "nombre": r.name} for r in carreras_rows]

        # Si aún no hay egresados con educación, devolver todas las carreras del catálogo
        if not carreras_list:
            todas = self.db.scalars(select(FieldOfStudy).order_by(FieldOfStudy.name)).all()
            carreras_list = [{"id": str(c.id), "nombre": c.name} for c in todas]

        # Períodos disponibles de colocaciones y encuestas
        periodos_set = set()
        
        # Años de inicio de colocaciones
        q_anios_col = select(func.to_char(Placement.start_date, 'YYYY')).distinct()
        if institution_id:
            q_anios_col = q_anios_col.where(Placement.institution_id == institution_id)
        for anio in self.db.scalars(q_anios_col).all():
            if anio:
                periodos_set.add(str(anio))

        # Períodos de encuestas
        q_per_enc = select(Survey.period).distinct()
        if institution_id:
            q_per_enc = q_per_enc.where(Survey.institution_id == institution_id)
        for per in self.db.scalars(q_per_enc).all():
            if per and per.strip():
                periodos_set.add(per.strip())

        # Si no hay períodos en BD, proponer los períodos recientes típicos
        if not periodos_set:
            current_year = datetime.now().year
            periodos_set = {str(current_year), str(current_year - 1), f"{current_year}-I", f"{current_year}-II"}

        return IndicadoresFiltrosOpciones(
            carreras=carreras_list,
            periodos=sorted(list(periodos_set), reverse=True),
        )

    def calcular_tablero(
        self,
        alcance: AlcanceStaff,
        carrera_id: uuid.UUID | None = None,
        periodo: str | None = None,
    ) -> IndicadoresResponse:
        """Calcula los indicadores de inserción laboral (HU-31) aplicando filtros de carrera y período.

        Regla de negocio:
        - Si total_colocaciones < 5 -> hay_suficientes_datos = False y mensaje "Sin datos suficientes".
        - Si total_colocaciones >= 5 -> calcula tasa, tiempo promedio, pertinencia y demanda de habilidades.
        """
        now = datetime.now(timezone.utc)
        institution_id = alcance.institution_id

        # 1. Resolver nombre de carrera si se especificó
        carrera_nombre = None
        if carrera_id:
            carrera_obj = self.db.get(FieldOfStudy, carrera_id)
            if carrera_obj:
                carrera_nombre = carrera_obj.name

        # 2. Base de Egresados (CandidateProfile + CandidateEducation)
        q_egresados = (
            select(CandidateProfile.id, CandidateEducation.graduation_date, CandidateEducation.start_date)
            .join(CandidateEducation, CandidateEducation.candidate_id == CandidateProfile.id)
            .where(CandidateProfile.verification_status == "verified")
        )
        if institution_id:
            q_egresados = q_egresados.where(CandidateProfile.institution_id == institution_id)
        if carrera_id:
            q_egresados = q_egresados.where(CandidateEducation.field_of_study_id == carrera_id)

        # Filtro de período sobre egreso si aplica formato año
        if periodo:
            # Puede matchear por año de egreso
            if len(periodo) == 4 and periodo.isdigit():
                q_egresados = q_egresados.where(func.to_char(CandidateEducation.graduation_date, 'YYYY') == periodo)

        egresados_rows = self.db.execute(q_egresados).all()
        # Mapeo de candidate_id -> graduation_date
        egresados_map = {}
        for row in egresados_rows:
            if row.id not in egresados_map or row.graduation_date:
                egresados_map[row.id] = row.graduation_date

        total_egresados = len(egresados_map)

        # 3. Base de Colocaciones (Placement)
        q_colocaciones = (
            select(Placement)
            .where(
                Placement.status == "confirmed",
                Placement.deleted_at.is_(None),
            )
        )
        if institution_id:
            q_colocaciones = q_colocaciones.where(Placement.institution_id == institution_id)
        if carrera_id:
            # El egresado debe tener la carrera seleccionada
            q_colocaciones = q_colocaciones.join(
                CandidateEducation, CandidateEducation.candidate_id == Placement.candidate_id
            ).where(CandidateEducation.field_of_study_id == carrera_id)
        if periodo:
            if len(periodo) == 4 and periodo.isdigit():
                q_colocaciones = q_colocaciones.where(func.to_char(Placement.start_date, 'YYYY') == periodo)

        colocaciones = self.db.scalars(q_colocaciones.distinct()).all()
        total_colocaciones = len(colocaciones)

        # 4. Base de Encuestas de Situación Laboral (HU-30)
        q_encuestas = (
            select(SurveyResponse)
            .join(Survey, Survey.id == SurveyResponse.survey_id)
        )
        if institution_id:
            q_encuestas = q_encuestas.where(Survey.institution_id == institution_id)
        if carrera_id:
            q_encuestas = q_encuestas.where(
                (Survey.field_of_study_id == carrera_id) | (Survey.field_of_study_id.is_(None))
            )
            # Y el egresado sea de esa carrera
            q_encuestas = q_encuestas.join(
                CandidateEducation, CandidateEducation.candidate_id == SurveyResponse.candidate_id
            ).where(CandidateEducation.field_of_study_id == carrera_id)
        if periodo:
            q_encuestas = q_encuestas.where(
                (Survey.period == periodo) | (func.to_char(SurveyResponse.submitted_at, 'YYYY') == periodo)
            )

        respuestas_encuestas = self.db.scalars(q_encuestas.distinct()).all()
        total_encuestas = len(respuestas_encuestas)

        # 5. Validación de la Regla de Negocio (CP03): Menos de 5 colocaciones
        if total_colocaciones < 5:
            return IndicadoresResponse(
                fecha_actualizacion=now,
                carrera_id=carrera_id,
                carrera_nombre=carrera_nombre,
                periodo=periodo,
                hay_suficientes_datos=False,
                mensaje_insuficiente="Sin datos suficientes (se requieren al menos 5 colocaciones registradas para el filtro seleccionado)",
                total_egresados=total_egresados,
                total_colocaciones=total_colocaciones,
                total_encuestas_respondidas=total_encuestas,
                tasa_colocacion=None,
                tiempo_promedio_primer_empleo_meses=None,
                pertinencia_empleo_porcentaje=None,
                habilidades_demandadas=[],
            )

        # 6. Cálculo de Indicadores con datos suficientes (>= 5 colocaciones)
        
        # A) Tasa de colocación (% egresados con colocación confirmada)
        # Aseguramos denominador representativo
        denominador_egresados = max(total_egresados, total_colocaciones)
        tasa_colocacion = round((total_colocaciones / denominador_egresados) * 100.0, 1) if denominador_egresados > 0 else 0.0
        if tasa_colocacion > 100.0:
            tasa_colocacion = 100.0

        # B) Tiempo promedio al primer empleo (en meses), con la misma regla que la exportación (HU-32):
        # lo que declararon en la encuesta laboral y, sin respuestas, de la fecha de egreso al inicio del empleo.
        # Sin ninguno de los dos queda en None ("Sin datos"), no en un valor estimado.
        ids_respuestas = [r.id for r in respuestas_encuestas]
        meses_encuesta = self._respuestas_numericas(ids_respuestas, "meses_primer_empleo")
        if meses_encuesta:
            tiempo_promedio = round(sum(meses_encuesta) / len(meses_encuesta), 1)
        else:
            diferencias_meses = [
                max(0.0, (col.start_date - egresados_map[col.candidate_id]).days / 30.4375)
                for col in colocaciones
                if egresados_map.get(col.candidate_id) and col.start_date
            ]
            tiempo_promedio = round(sum(diferencias_meses) / len(diferencias_meses), 1) if diferencias_meses else None

        # C) Pertinencia del empleo: pregunta "relación con la carrera" de la encuesta (escala 1 a 5).
        # El cargo de la colocación no dice si el empleo es acorde a la carrera: sin respuestas queda en None.
        relacion = self._respuestas_numericas(ids_respuestas, "relacion_carrera")
        pertinencia_pct = round(sum(relacion) / len(relacion) / 5.0 * 100.0, 1) if relacion else None

        # D) Demanda de Habilidades
        # Extraemos las habilidades de los candidatos colocados
        candidatos_colocados_ids = list({col.candidate_id for col in colocaciones})
        q_skills = (
            select(Skill.name, func.count(CandidateSkill.candidate_id))
            .join(Skill, Skill.id == CandidateSkill.skill_id)
            .where(CandidateSkill.candidate_id.in_(candidatos_colocados_ids))
            .group_by(Skill.name)
            .order_by(func.count(CandidateSkill.candidate_id).desc())
            .limit(6)
        )
        skills_res = self.db.execute(q_skills).all()

        # Si los colocados no cargaron habilidades la lista queda vacía (la pantalla lo indica).
        habilidades_list = [
            HabilidadDemandaItem(
                nombre=s_name, total=s_count, porcentaje=round((s_count / len(candidatos_colocados_ids)) * 100.0, 1)
            )
            for s_name, s_count in skills_res
        ]

        return IndicadoresResponse(
            fecha_actualizacion=now,
            carrera_id=carrera_id,
            carrera_nombre=carrera_nombre,
            periodo=periodo,
            hay_suficientes_datos=True,
            mensaje_insuficiente=None,
            total_egresados=total_egresados,
            total_colocaciones=total_colocaciones,
            total_encuestas_respondidas=total_encuestas,
            tasa_colocacion=tasa_colocacion,
            tiempo_promedio_primer_empleo_meses=tiempo_promedio,
            pertinencia_empleo_porcentaje=pertinencia_pct,
            habilidades_demandadas=habilidades_list,
        )

    def _respuestas_numericas(self, ids_respuestas: list[uuid.UUID], codigo: str) -> list[float]:
        """Valores numéricos que los egresados dieron a una pregunta de la encuesta laboral (por su código)."""
        if not ids_respuestas:
            return []
        valores = self.db.scalars(
            select(SurveyAnswer.answer_number)
            .join(SurveyQuestion, SurveyQuestion.id == SurveyAnswer.question_id)
            .where(
                SurveyAnswer.response_id.in_(ids_respuestas),
                SurveyQuestion.code == codigo,
                SurveyAnswer.answer_number.is_not(None),
            )
        ).all()
        return [float(v) for v in valores]
