"""Servicio de cálculo y exportación de indicadores de inserción laboral (HU-31 y HU-32).

Calcula la tasa de colocación, tiempo al primer empleo, pertinencia con la carrera
y habilidades demandadas a partir de colocaciones (HU-29) y encuestas periódicas (HU-30).
Exporta el tablero completo a PDF y Excel (.xlsx) con auditoría y control de significancia muestral (CP04).
"""

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.features.bitacora.service import BitacoraService
from app.features.reportes.indicadores_schema import (
    HabilidadDemandaDTO,
    TableroIndicadoresResponse,
)
from app.models.candidato import CandidateEducation, CandidateProfile
from app.models.catalogo import FieldOfStudy, Skill
from app.models.colocacion import Placement
from app.models.encuesta import Survey, SurveyAnswer, SurveyQuestion, SurveyResponse
from app.models.institucion import Institution
from app.models.postulacion import Application
from app.models.usuario import AppUser
from app.models.vacante import JobPosting, JobSkill, JobStatus
from app.shared.exportacion import Tabla, a_excel, a_pdf, hora_bolivia


@dataclass
class ReporteIndicadoresArchivo:
    contenido: bytes
    tipo: str
    nombre: str
    total: int


class IndicadoresService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def calcular_tablero(
        self,
        institucion_id: uuid.UUID | None,
        carrera_id: uuid.UUID | None = None,
        periodo: str | None = None,
    ) -> TableroIndicadoresResponse:
        """Calcula todas las métricas del tablero de indicadores (HU-31).

        Aplica filtros por institución, carrera y período, y valida significancia muestral (CP04).
        """
        ahora = datetime.now(timezone.utc)

        # 1. Recuperar nombres de contexto (institución y carrera)
        institucion_nombre = None
        if institucion_id:
            inst = self.db.get(Institution, institucion_id)
            if inst:
                institucion_nombre = inst.name

        carrera_nombre = None
        if carrera_id:
            carr = self.db.get(FieldOfStudy, carrera_id)
            if carr:
                carrera_nombre = carr.name

        # 2. Consultar universo de egresados de la institución
        q_egresados = select(CandidateProfile.id).join(AppUser, AppUser.id == CandidateProfile.user_id)
        if institucion_id:
            q_egresados = q_egresados.where(CandidateProfile.institution_id == institucion_id)

        if carrera_id:
            q_egresados = q_egresados.where(
                CandidateProfile.educations.any(CandidateEducation.field_of_study_id == carrera_id)
            )

        egresados_ids = list(self.db.scalars(q_egresados).all())
        total_egresados = len(egresados_ids)

        # 3. Consultar Colocaciones (HU-29)
        q_colocaciones = select(Placement).where(
            Placement.status.in_(("confirmed", "suggested")),
            Placement.deleted_at.is_(None),
        )
        if institucion_id:
            q_colocaciones = q_colocaciones.where(Placement.institution_id == institucion_id)

        if egresados_ids:
            q_colocaciones = q_colocaciones.where(Placement.candidate_id.in_(egresados_ids))
        elif institucion_id or carrera_id:
            # Si se filtró por carrera o institución y no hay egresados, forzar lista vacía
            q_colocaciones = q_colocaciones.where(Placement.id == uuid.UUID(int=0))

        if periodo and periodo.strip():
            # Filtrar por año o prefijo en start_date
            anio_str = periodo.strip().split("-")[0]
            if anio_str.isdigit() and len(anio_str) == 4:
                q_colocaciones = q_colocaciones.where(
                    func.extract("year", Placement.start_date) == int(anio_str)
                )

        colocaciones = list(self.db.scalars(q_colocaciones).all())
        total_colocados = len({col.candidate_id for col in colocaciones})

        # 4. Consultar Respuestas de Encuestas (HU-30)
        q_respuestas = (
            select(SurveyResponse)
            .join(Survey, Survey.id == SurveyResponse.survey_id)
            .where(Survey.is_active.is_(True))
        )
        if institucion_id:
            q_respuestas = q_respuestas.where(
                or_(Survey.institution_id == institucion_id, Survey.target_scope == "all_candidates")
            )
        if carrera_id:
            q_respuestas = q_respuestas.where(
                or_(Survey.field_of_study_id == carrera_id, Survey.field_of_study_id.is_(None))
            )
        if egresados_ids:
            q_respuestas = q_respuestas.where(SurveyResponse.candidate_id.in_(egresados_ids))
        elif institucion_id or carrera_id:
            q_respuestas = q_respuestas.where(SurveyResponse.id == uuid.UUID(int=0))

        if periodo and periodo.strip():
            q_respuestas = q_respuestas.where(Survey.period.ilike(f"%{periodo.strip()}%"))

        encuestas = list(self.db.scalars(q_respuestas).all())
        total_encuestas = len(encuestas)

        # 5. Cálculo de Tasa de Colocación
        # Si hay egresados registrados, base = total_egresados; si no, base = encuestas + colocados
        base_muestra = max(total_egresados, len(colocaciones), total_encuestas)
        if base_muestra > 0:
            tasa_colocacion = min(100.0, (total_colocados / base_muestra) * 100.0)
        else:
            tasa_colocacion = 0.0

        # 6. Cálculo de Tiempo Promedio al Primer Empleo (meses)
        # Se obtiene a partir de respuestas en encuestas (pregunta 'meses_primer_empleo')
        # o colocaciones registradas
        q_meses = (
            select(SurveyAnswer.answer_number)
            .join(SurveyQuestion, SurveyQuestion.id == SurveyAnswer.question_id)
            .join(SurveyResponse, SurveyResponse.id == SurveyAnswer.response_id)
            .where(
                SurveyQuestion.code == "meses_primer_empleo",
                SurveyAnswer.answer_number.is_not(None),
            )
        )
        if egresados_ids:
            q_meses = q_meses.where(SurveyResponse.candidate_id.in_(egresados_ids))
        elif institucion_id or carrera_id:
            # Sin egresados en el filtro no se promedian respuestas de otras universidades.
            q_meses = q_meses.where(SurveyResponse.id == uuid.UUID(int=0))

        valores_meses = [float(v) for v in self.db.scalars(q_meses).all() if v is not None and v >= 0]
        if valores_meses:
            tiempo_promedio = sum(valores_meses) / len(valores_meses)
        else:
            # Sin respuestas de encuesta: se mide desde el egreso hasta el primer empleo registrado.
            tiempo_promedio = self._meses_desde_egreso(colocaciones)

        # 7. Cálculo de Pertinencia Laboral con la Carrera (%)
        # Pregunta 'relacion_carrera' en escala 1-5
        q_pertinencia = (
            select(SurveyAnswer.answer_number)
            .join(SurveyQuestion, SurveyQuestion.id == SurveyAnswer.question_id)
            .join(SurveyResponse, SurveyResponse.id == SurveyAnswer.response_id)
            .where(
                SurveyQuestion.code == "relacion_carrera",
                SurveyAnswer.answer_number.is_not(None),
            )
        )
        if egresados_ids:
            q_pertinencia = q_pertinencia.where(SurveyResponse.candidate_id.in_(egresados_ids))
        elif institucion_id or carrera_id:
            q_pertinencia = q_pertinencia.where(SurveyResponse.id == uuid.UUID(int=0))

        valores_pertinencia = [float(v) for v in self.db.scalars(q_pertinencia).all() if v is not None and v > 0]
        if valores_pertinencia:
            # Escala 1 a 5 convertida a 0 a 100%
            promedio_escala = sum(valores_pertinencia) / len(valores_pertinencia)
            pertinencia_carrera = (promedio_escala / 5.0) * 100.0
        else:
            # Solo la encuesta mide la relación con la carrera: sin respuestas no hay dato.
            pertinencia_carrera = None

        # 8. Demanda de Habilidades Laborales
        # Se analizan las habilidades requeridas en vacantes activas y colocaciones
        q_skills = (
            select(Skill.name, func.count(JobSkill.job_posting_id))
            .join(JobSkill, JobSkill.skill_id == Skill.id)
            .join(JobPosting, JobPosting.id == JobSkill.job_posting_id)
            .where(JobPosting.status == JobStatus.PUBLISHED.value)
            .group_by(Skill.name)
            .order_by(func.count(JobSkill.job_posting_id).desc())
            .limit(10)
        )
        filas_skills = self.db.execute(q_skills).all()
        total_menciones_skills = sum(count for _, count in filas_skills) or 1
        top_habilidades: list[HabilidadDemandaDTO] = []
        for nombre, count in filas_skills:
            pct = round((count / total_menciones_skills) * 100.0, 1)
            top_habilidades.append(
                HabilidadDemandaDTO(habilidad=nombre, total_menciones=count, porcentaje=pct)
            )

        # 9. Distribución de modalidades: la de la vacante cuando la colocación vino de una postulación.
        colocaciones_por_modalidad = {"onsite": 0, "hybrid": 0, "remote": 0, "sin_dato": 0}
        postulaciones = [col.application_id for col in colocaciones if col.application_id]
        modalidad_por_postulacion = (
            dict(
                self.db.execute(
                    select(Application.id, JobPosting.work_modality)
                    .join(JobPosting, JobPosting.id == Application.job_id)
                    .where(Application.id.in_(postulaciones))
                ).all()
            )
            if postulaciones
            else {}
        )
        for col in colocaciones:
            modalidad = modalidad_por_postulacion.get(col.application_id)
            colocaciones_por_modalidad[modalidad if modalidad in colocaciones_por_modalidad else "sin_dato"] += 1

        # 10. Validación de Significancia Muestral (CP04: < 5 casos)
        muestra_total = max(base_muestra, len(colocaciones), len(valores_meses), len(valores_pertinencia))
        muestra_suficiente = muestra_total >= 5
        advertencia_muestra = None
        if not muestra_suficiente:
            advertencia_muestra = (
                "Muestra insuficiente (< 5 casos) para garantizar significancia estadística. "
                "Los indicadores deben interpretarse con cautela."
            )

        return TableroIndicadoresResponse(
            institucion_id=institucion_id,
            institucion_nombre=institucion_nombre or "Todas las instituciones",
            carrera_id=carrera_id,
            carrera_nombre=carrera_nombre or "Todas las carreras",
            periodo=periodo or "Histórico general",
            calculado_en=ahora,
            tasa_colocacion=round(tasa_colocacion, 1),
            tiempo_promedio_primer_empleo_meses=round(tiempo_promedio, 1) if tiempo_promedio is not None else None,
            pertinencia_carrera_porcentaje=round(pertinencia_carrera, 1) if pertinencia_carrera is not None else None,
            total_egresados_muestra=muestra_total,
            total_colocados=total_colocados,
            total_encuestas_respondidas=total_encuestas,
            muestra_suficiente=muestra_suficiente,
            advertencia_muestra=advertencia_muestra,
            top_habilidades_demandadas=top_habilidades,
            colocaciones_por_modalidad=colocaciones_por_modalidad,
        )

    def _meses_desde_egreso(self, colocaciones: list[Placement]) -> float | None:
        """Promedio de meses entre la fecha de egreso y el primer empleo; None si ningún colocado tiene fecha de egreso."""
        primer_empleo: dict[uuid.UUID, date] = {}
        for col in colocaciones:
            if col.candidate_id not in primer_empleo or col.start_date < primer_empleo[col.candidate_id]:
                primer_empleo[col.candidate_id] = col.start_date
        if not primer_empleo:
            return None
        egreso = dict(
            self.db.execute(
                select(CandidateEducation.candidate_id, func.max(CandidateEducation.graduation_date))
                .where(
                    CandidateEducation.candidate_id.in_(primer_empleo),
                    CandidateEducation.graduation_date.is_not(None),
                )
                .group_by(CandidateEducation.candidate_id)
            ).all()
        )
        meses = [
            max(0.0, (inicio - egreso[candidato]).days / 30.4375)
            for candidato, inicio in primer_empleo.items()
            if candidato in egreso
        ]
        return sum(meses) / len(meses) if meses else None

    def exportar(
        self,
        institucion_id: uuid.UUID | None,
        carrera_id: uuid.UUID | None,
        periodo: str | None,
        formato: Literal["pdf", "xlsx", "excel"],
        usuario_id: uuid.UUID | None,
        correo: str | None = None,
        ip_address: str | None = None,
    ) -> ReporteIndicadoresArchivo:
        """Exporta el reporte del tablero de indicadores a PDF o Excel (HU-32).

        Criterios de aceptación HU-32:
        - CP01: Exportación a PDF con formato institucional legible, fecha/hora Bolivia y filtros.
        - CP02: Exportación a Excel (.xlsx) con celdas estructuradas y estilos corporativos.
        - CP03: Registro de la operación de exportación en la bitácora de auditoría (audit_log).
        - CP04: Manejo correcto cuando hay muestra insuficiente (< 5 casos) sin generar fallos ni divisiones por cero.
        """
        tablero = self.calcular_tablero(institucion_id=institucion_id, carrera_id=carrera_id, periodo=periodo)
        ahora_bol = hora_bolivia(tablero.calculado_en)
        fecha_str = ahora_bol.strftime("%d/%m/%Y %H:%M")

        descripcion_lineas = [
            f"Institución: {tablero.institucion_nombre}",
            f"Carrera: {tablero.carrera_nombre}",
            f"Período evaluado: {tablero.periodo}",
            f"Generado por: {correo or 'Administrador Universitario'} | Fecha de emisión: {fecha_str} (Hora de Bolivia)",
        ]

        if not tablero.muestra_suficiente:
            descripcion_lineas.append(
                "ADVERTENCIA METODOLÓGICA: Muestra insuficiente (< 5 registros). "
                "Los datos se presentan únicamente con fines preliminares sin significancia estadística."
            )

        encabezados = ["Indicador Clave", "Valor Obtenido", "Muestra (N)", "Estado / Interpretación"]

        # Formatear filas con explicabilidad
        tiempo = tablero.tiempo_promedio_primer_empleo_meses
        pertinencia = tablero.pertinencia_carrera_porcentaje
        sin_datos = "Sin datos registrados"
        estado_tasa = "Inserción alta" if tablero.tasa_colocacion >= 70 else ("Inserción media" if tablero.tasa_colocacion >= 40 else "Inserción en desarrollo")
        estado_tiempo = sin_datos if tiempo is None else ("Inserción rápida" if tiempo <= 6 else "Inserción progresiva")
        estado_pertinencia = sin_datos if pertinencia is None else ("Alta pertinencia" if pertinencia >= 75 else "Pertinencia moderada")

        habs_resumen = ", ".join(f"{h.habilidad} ({h.porcentaje}%)" for h in tablero.top_habilidades_demandadas[:4])

        filas = [
            [
                "Tasa de Colocación Laboral",
                f"{tablero.tasa_colocacion:.1f}%",
                tablero.total_egresados_muestra,
                estado_tasa if tablero.muestra_suficiente else "Muestra insuficiente (< 5 casos)",
            ],
            [
                "Tiempo Promedio al Primer Empleo",
                f"{tiempo:.1f} meses" if tiempo is not None else "Sin datos",
                tablero.total_egresados_muestra,
                estado_tiempo if tablero.muestra_suficiente else "Muestra insuficiente (< 5 casos)",
            ],
            [
                "Pertinencia con la Carrera Cursada",
                f"{pertinencia:.1f}%" if pertinencia is not None else "Sin datos",
                tablero.total_egresados_muestra,
                estado_pertinencia if tablero.muestra_suficiente else "Muestra insuficiente (< 5 casos)",
            ],
            [
                "Habilidades Más Demandadas",
                habs_resumen or "Sin datos",
                len(tablero.top_habilidades_demandadas),
                "Top habilidades requeridas por empleadores" if habs_resumen else "Sin vacantes publicadas con habilidades",
            ],
        ]

        tabla = Tabla(
            titulo="Tablero de Indicadores de Inserción Laboral - EGRESA",
            descripcion=descripcion_lineas,
            encabezados=encabezados,
            filas=filas,
            tipos=["texto", "texto", "numero", "texto"],
        )

        nombre_base = f"reporte_indicadores_{ahora_bol.strftime('%Y%m%d_%H%M')}"

        if formato == "pdf":
            contenido = a_pdf(tabla)
            tipo_mime = "application/pdf"
            nombre_archivo = f"{nombre_base}.pdf"
        else:
            contenido = a_excel(tabla)
            tipo_mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            nombre_archivo = f"{nombre_base}.xlsx"

        # Registrar en la bitácora de auditoría (CP03); con la clave configurada la entrada se guarda cifrada.
        if usuario_id is not None:
            BitacoraService(self.db).registrar(
                modulo="reportes",
                accion="exportar_reporte_indicadores",
                usuario_id=usuario_id,
                ip=ip_address,
                detalles=(
                    f"formato={formato}; carrera_id={carrera_id or 'todas'}; periodo={periodo or 'historico'}; "
                    f"total_muestra={tablero.total_egresados_muestra}; muestra_suficiente={tablero.muestra_suficiente}"
                ),
            )
            self.db.commit()

        return ReporteIndicadoresArchivo(
            contenido=contenido,
            tipo=tipo_mime,
            nombre=nombre_archivo,
            total=tablero.total_egresados_muestra,
        )

