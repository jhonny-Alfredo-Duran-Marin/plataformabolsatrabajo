"""Servicio de Búsqueda Semántica de Vacantes con IA (HU-25).

Interpreta consultas en lenguaje natural (ej. "quiero trabajar programando sin atención al público",
"backend python remoto") evaluando la intención de búsqueda, puntuando la relevancia semántica
(0-100) y ofreciendo explicabilidad de coincidencia.
Soporta filtros estructurados complementarios y degradación elegante si la IA no está disponible.
"""

import re
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.config import get_settings
from app.features.ia.schema import BusquedaSemanticaResponse, VacanteSemanticaItemDTO
from app.features.moderacion.reglas import no_oculta_por_denuncias
from app.models.catalogo import JobCategory
from app.models.empresa import Company
from app.models.institucion import CompanyInstitution
from app.models.vacante import JobPosting, JobSkill, JobStatus


def _empresa_vinculada(institution_id: uuid.UUID):
    return (
        select(CompanyInstitution.company_id)
        .where(
            CompanyInstitution.company_id == JobPosting.company_id,
            CompanyInstitution.institution_id == institution_id,
            CompanyInstitution.status.in_(("approved",)),
        )
        .exists()
    )


class SemanticSearchService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def buscar(
        self,
        q: str,
        ciudad: str | None = None,
        modalidad: str | None = None,
        carrera_id: uuid.UUID | None = None,
        salario_min: Decimal | None = None,
        seniority: str | None = None,
        institution_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> BusquedaSemanticaResponse:
        """Ejecuta una búsqueda semántica de vacantes en lenguaje natural.

        Cumple con los criterios de aceptación de HU-25:
        - CP01: Búsqueda en lenguaje natural interpretando intención, score semántico (0-100) y razón de coincidencia.
        - CP02: Si no existen coincidencias cercanas, ofrece sugerencias para ampliar la búsqueda.
        - CP03: Combinación de búsqueda semántica con filtros estructurados (ciudad, modalidad, etc.).
        - CP04: Si el servicio de IA está apagado, degrada elegantemente a coincidencia léxica sin romper la búsqueda.
        """
        consulta_limpia = q.strip() if q else ""
        ia_activa = bool(get_settings().ia_recomendaciones_activas)

        # 1. Interpretar intención semántica
        intencion = self._interpretar_intencion(consulta_limpia)

        # 2. Consultar vacantes vigentes y visibles
        query = (
            select(JobPosting)
            .options(
                joinedload(JobPosting.company),
                joinedload(JobPosting.category),
                selectinload(JobPosting.skills).selectinload(JobSkill.skill),
            )
            .where(
                JobPosting.status == JobStatus.PUBLISHED.value,
                no_oculta_por_denuncias(),
                JobPosting.company.has(Company.account_status != "suspended"),
            )
        )

        if institution_id:
            query = query.where(_empresa_vinculada(institution_id))

        # 3. Aplicar filtros estructurados
        if ciudad and ciudad.strip():
            query = query.where(JobPosting.city.ilike(f"%{ciudad.strip()}%"))

        if modalidad and modalidad.strip():
            query = query.where(JobPosting.work_modality == modalidad.strip())

        if seniority and seniority.strip():
            query = query.where(JobPosting.seniority_level == seniority.strip())

        if salario_min is not None and salario_min > 0:
            query = query.where(
                or_(
                    JobPosting.salary_max >= salario_min,
                    JobPosting.salary_min >= salario_min,
                )
            )

        vacantes_disponibles = list(self.db.execute(query).unique().scalars().all())

        # 4. Calcular puntajes semánticos
        items_con_score: list[tuple[JobPosting, int, str]] = []

        for v in vacantes_disponibles:
            if ia_activa:
                score, razon = self._calcular_score_semantico(v, consulta_limpia, intencion)
            else:
                # Degradación elegante (CP04): coincidencia léxica básica
                score, razon = self._calcular_score_fallback(v, consulta_limpia)

            # Umbral mínimo de relevancia para no retornar ruido absoluto
            if score >= 20 or not consulta_limpia:
                items_con_score.append((v, score, razon))

        # 5. Ordenar por relevancia descendente
        items_con_score.sort(key=lambda x: x[1], reverse=True)

        # 6. Paginación
        total = len(items_con_score)
        offset = (max(page, 1) - 1) * page_size
        paginados = items_con_score[offset : offset + page_size]

        # 7. Convertir a DTO
        resultados: list[VacanteSemanticaItemDTO] = []
        for vacante, score, razon in paginados:
            empresa_nombre = (
                (vacante.company.trade_name or vacante.company.legal_name)
                if vacante.company
                else "Empresa confidencial"
            )
            resultados.append(
                VacanteSemanticaItemDTO(
                    id=vacante.id,
                    title=vacante.title,
                    company_name=empresa_nombre,
                    city=vacante.city,
                    work_modality=vacante.work_modality,
                    seniority_level=vacante.seniority_level,
                    employment_type=vacante.employment_type,
                    salary_min=vacante.salary_min,
                    salary_max=vacante.salary_max,
                    currency=vacante.currency or "BOB",
                    description=vacante.description,
                    score_relevancia=score,
                    razon_coincidencia=razon,
                    published_at=vacante.published_at,
                )
            )

        # 8. Generar sugerencias si no hay resultados o relevancia es baja (CP02)
        sugerencia = None
        if not ia_activa:
            sugerencia = (
                "Búsqueda ejecutada en modo de compatibilidad estructurada (el microservicio semántico de IA está "
                "temporalmente en mantenimiento)."
            )
        elif total == 0 or (total > 0 and items_con_score[0][1] < 45):
            sugerencias_textos = []
            if intencion.get("excluye_atencion_publico"):
                sugerencias_textos.append("términos como 'desarrollador', 'analista de sistemas' o 'backend'")
            if intencion.get("modalidad_preferida") == "remote":
                sugerencias_textos.append("ampliar la modalidad a 'híbrido' o 'presencial'")
            if not sugerencias_textos:
                sugerencias_textos.append("palabras clave más generales o revisar los filtros aplicados")

            sugerencia = (
                f"No se encontraron vacantes con alta afinidad exacta. Te sugerimos intentar con "
                f"{', '.join(sugerencias_textos)}."
            )

        return BusquedaSemanticaResponse(
            total=total,
            consulta_original=consulta_limpia,
            intencion_interpretada=intencion,
            ia_disponible=ia_activa,
            sugerencia=sugerencia,
            items=resultados,
        )

    def _interpretar_intencion(self, q: str) -> dict[str, Any]:
        """Interpreta conceptos, temas y restricciones a partir de la consulta en lenguaje natural."""
        texto = q.lower()
        intencion: dict[str, Any] = {
            "area_tecnica": False,
            "excluye_atencion_publico": False,
            "modalidad_preferida": None,
            "seniority_preferido": None,
            "terminos_clave": [],
        }

        # Detección de área técnica / desarrollo
        if any(w in texto for w in ("program", "desarroll", "backend", "frontend", "software", "codigo", "código", "sistemas", "dev")):
            intencion["area_tecnica"] = True

        # Detección de restricción "sin atención al público" / "sin clientes" / "no ventas"
        if any(w in texto for w in (
            "sin atención al público", "sin atencion al publico", "sin clientes", "no clientes",
            "sin hablar con clientes", "sin llamadas", "no ventas", "sin atencion", "sin atención",
        )):
            intencion["excluye_atencion_publico"] = True

        # Detección de modalidad
        if any(w in texto for w in ("remoto", "teletrabajo", "home office", "desde casa")):
            intencion["modalidad_preferida"] = "remote"
        elif any(w in texto for w in ("hibrido", "híbrido", "mixto")):
            intencion["modalidad_preferida"] = "hybrid"
        elif any(w in texto for w in ("presencial", "en oficina")):
            intencion["modalidad_preferida"] = "onsite"

        # Detección de seniority
        if any(w in texto for w in ("junior", "jr", "sin experiencia", "primer empleo", "recién graduado", "pasante")):
            intencion["seniority_preferido"] = "junior"
        elif any(w in texto for w in ("senior", "sr", "líder", "experto")):
            intencion["seniority_preferido"] = "senior"

        # Extraer palabras clave relevantes (filtrar stopwords)
        stopwords = {
            "de", "la", "el", "los", "las", "un", "una", "unos", "unas", "y", "o", "en", "para", "por",
            "con", "sin", "al", "del", "que", "como", "quiero", "trabajar", "busco", "necesito", "deseo",
            "trabajo", "empleo", "vacante", "vacantes", "vigente", "vigentes", "oferta", "ofertas",
        }
        palabras = re.findall(r"\b[a-záéíóúñ]{3,}\b", texto)
        terminos = [p for p in palabras if p not in stopwords]
        intencion["terminos_clave"] = terminos[:8]

        return intencion

    def _calcular_score_semantico(
        self,
        vacante: JobPosting,
        consulta: str,
        intencion: dict[str, Any],
    ) -> tuple[int, str]:
        """Calcula el puntaje de afinidad semántica (0-100) y genera la justificación."""
        score = 0
        razones = []
        texto_vacante = f"{vacante.title} {vacante.description}".lower()
        skills_nombres = [js.skill.name.lower() for js in (vacante.skills or []) if js.skill]
        skills_texto = " ".join(skills_nombres)

        # 1. Alineación con Área Técnica / Programación
        es_vacante_tecnica = any(
            t in texto_vacante or t in skills_texto
            for t in ("desarrollo", "software", "programador", "backend", "frontend", "sistemas", "python", "developer")
        )

        if intencion.get("area_tecnica"):
            if es_vacante_tecnica:
                score += 40
                razones.append("perfil de desarrollo técnico y software")
            else:
                score += 5

        # 2. Restricción Semántica: Sin Atención al Público
        if intencion.get("excluye_atencion_publico"):
            es_atencion_o_ventas = any(
                w in texto_vacante
                for w in ("atención al cliente", "atencion al cliente", "call center", "ventas", "vendedor", "recepción", "caja")
            )
            if not es_atencion_o_ventas and es_vacante_tecnica:
                score += 25
                razones.append("rol enfocado en trabajo técnico sin atención a clientes")
            elif es_atencion_o_ventas:
                score -= 35
                razones.append("penalizado por requerir atención o ventas")

        # 3. Concordancia de Modalidad
        mod_deseada = intencion.get("modalidad_preferida")
        if mod_deseada:
            if vacante.work_modality == mod_deseada:
                score += 20
                mod_desc = "remota" if mod_deseada == "remote" else mod_deseada
                razones.append(f"modalidad {mod_desc}")
            elif mod_deseada == "remote" and vacante.work_modality == "hybrid":
                score += 10
                razones.append("modalidad híbrida flexible")

        # 4. Concordancia de Seniority
        seniority_deseado = intencion.get("seniority_preferido")
        if seniority_deseado and vacante.seniority_level == seniority_deseado:
            score += 20
            razones.append(f"nivel {seniority_deseado}")

        # 5. Concordancia con Términos Clave de la Consulta: pesa la proporción de términos
        # encontrados, así una búsqueda de una sola palabra ("python") que coincide supera el umbral.
        terminos = intencion.get("terminos_clave", [])
        coincidentes = [t for t in terminos if t in texto_vacante or t in skills_texto]
        if coincidentes:
            score += round(50 * len(coincidentes) / len(terminos))
            razones.append(f"términos de tu búsqueda ({', '.join(coincidentes[:3])})")

        # 6. Consulta vacía o solo con palabras genéricas ("vacantes vigentes"): puntaje estándar de novedad
        if not consulta or not any(intencion.values()):
            score = 60
            razones.append("vacante destacada vigente")

        # Ajuste a rango 0 - 100
        score_final = max(0, min(100, score))

        if not razones:
            razon_texto = "Coincidencia contextual con el perfil general de la vacante."
        else:
            razon_texto = f"Coincidencia alta por {', '.join(razones)}."

        return score_final, razon_texto

    def _calcular_score_fallback(self, vacante: JobPosting, consulta: str) -> tuple[int, str]:
        """Degradación elegante: puntaje básico por palabras clave sin IA."""
        if not consulta:
            return 50, "Búsqueda estándar sin términos especificados."

        palabras = [p.lower() for p in consulta.split() if len(p) > 2]
        texto_completo = f"{vacante.title} {vacante.description}".lower()
        aciertos = [p for p in palabras if p in texto_completo]

        if not aciertos:
            return 20, "Coincidencia mínima con el catálogo general de vacantes."

        porcentaje = int((len(aciertos) / len(palabras)) * 70) + 20
        porcentaje = min(porcentaje, 90)
        return (
            porcentaje,
            f"Coincidencia por palabras clave: {', '.join(aciertos[:3])} (modo compatibilidad sin IA).",
        )

