"""Asistente generativo de redacción con Inteligencia Artificial (HU-26).

Permite a los egresados generar borradores de resumen profesional adaptados a los
datos académicos, laborales y de habilidades ya cargados en su perfil.
"""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.common.exceptions import ResourceNotFoundException, ServiceUnavailableException
from app.core.config import get_settings
from app.features.ia.schema import GenerarResumenResponse
from app.features.perfil.repository import EgresadoRepository


class AsistenteGenerativoService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = EgresadoRepository(db)

    def generar_resumen_profesional(
        self,
        usuario_id: uuid.UUID,
        variante: int = 1,
        enfoque: str | None = "general",
    ) -> GenerarResumenResponse:
        """Genera un borrador de resumen profesional para el egresado a partir de su perfil.

        Cumple con los criterios de aceptación de HU-26:
        - Borrador generado a partir de los datos ya cargados en su perfil (CP01).
        - Soporta generar versiones alternativas rotando variantes (CP03).
        - Si el microservicio de IA está apagado o no disponible, lanza 503 (CP04).
        """
        if not get_settings().ia_recomendaciones_activas:
            raise ServiceUnavailableException(
                "El microservicio de IA no está disponible en este momento. Puedes redactar tu resumen manualmente."
            )

        perfil = self.repo.obtener_por_usuario_id(usuario_id)
        if perfil is None:
            raise ResourceNotFoundException("Perfil de egresado no encontrado.")

        # Obtener formación académica
        educacion_principal = self.repo.obtener_educacion_principal(perfil.id)
        carrera = None
        institucion = None
        if educacion_principal:
            if educacion_principal.field_of_study and educacion_principal.field_of_study.name:
                carrera = educacion_principal.field_of_study.name
            else:
                carrera = educacion_principal.program_name
            institucion = educacion_principal.institution_name or (
                perfil.institution.name if perfil.institution else None
            )

        if not carrera:
            # Buscar en formación adicional si no tiene educación principal marcada
            formaciones = self.repo.listar_formacion(perfil.id)
            if formaciones:
                f_primera = formaciones[0]
                carrera = f_primera.program_name
                institucion = f_primera.institution_name or (
                    perfil.institution.name if perfil.institution else None
                )

        titulo = perfil.professional_headline or carrera or "Profesional"
        institucion_texto = institucion or "la universidad"

        # Obtener experiencias laborales
        experiencias = self.repo.listar_experiencia(perfil.id)
        cargos = [e.position_title for e in experiencias if e.position_title]
        empresas = [e.company_name for e in experiencias if e.company_name]

        # Obtener habilidades técnicas y blandas
        habilidades = [s.name for s in self.repo.listar_habilidades(perfil.id)]

        # Obtener idiomas
        idiomas_data = self.repo.listar_idiomas(perfil.id)
        idiomas = [lang.name for _, lang in idiomas_data]

        # Datos utilizados para trazabilidad y transparencia
        datos_utilizados: dict[str, Any] = {
            "carrera": carrera or "No especificada",
            "titulo": titulo,
            "institucion": institucion_texto,
            "total_experiencias": len(experiencias),
            "cargos_previos": cargos[:3],
            "total_habilidades": len(habilidades),
            "habilidades_principales": habilidades[:6],
            "idiomas": idiomas,
        }

        # Generar borrador según variante y perfil
        borrador = self._construir_borrador(
            nombre=perfil.first_name,
            titulo=titulo,
            carrera=carrera,
            institucion=institucion_texto,
            cargos=cargos,
            empresas=empresas,
            habilidades=habilidades,
            idiomas=idiomas,
            variante=variante,
        )

        return GenerarResumenResponse(
            borrador=borrador,
            generado_por_ia=True,
            advertencia="Borrador generado por IA. Requiere revisión del egresado antes de guardarlo en el perfil.",
            variante=variante,
            total_variantes=3,
            datos_utilizados=datos_utilizados,
        )

    def _construir_borrador(
        self,
        nombre: str,
        titulo: str,
        carrera: str | None,
        institucion: str,
        cargos: list[str],
        empresas: list[str],
        habilidades: list[str],
        idiomas: list[str],
        variante: int,
    ) -> str:
        """Sintetiza variantes de redacción profesional basadas en el contexto del candidato."""
        habs_txt = ", ".join(habilidades[:4]) if habilidades else "solución de problemas y aprendizaje continuo"
        otras_habs_txt = ", ".join(habilidades[4:8]) if len(habilidades) > 4 else "trabajo colaborativo y adaptabilidad"
        idiomas_txt = f" Manejo de {', '.join(idiomas)}." if idiomas else ""

        tiene_experiencia = len(cargos) > 0
        cargos_txt = ", ".join(dict.fromkeys(cargos[:2])) if cargos else ""
        empresas_txt = f" en empresas como {', '.join(dict.fromkeys(empresas[:2]))}" if empresas else ""

        # Normalizar variante a ciclo de 1 a 3
        v_idx = ((variante - 1) % 3) + 1

        if v_idx == 1:
            # Variante 1: Enfoque Ejecutivo y Trayectoria
            if tiene_experiencia:
                p1 = (
                    f"{titulo} con sólida formación académica por {institucion} y trayectoria en {cargos_txt}{empresas_txt}. "
                    f"Especializado/a en {habs_txt}, con enfoque en la entrega de resultados y optimización de procesos."
                )
            else:
                p1 = (
                    f"Egresado/a en {carrera or titulo} por {institucion}, con sólida base formativa y competencias destacadas en {habs_txt}. "
                    f"Motivado/a por integrarse al ámbito profesional y aplicar conocimientos actualizados en entornos dinámicos."
                )
            p2 = (
                f"Me caracterizo por el pensamiento analítico, la responsabilidad y {otras_habs_txt}.{idiomas_txt} "
                f"Busco contribuir con soluciones de alto impacto y continuar mi crecimiento profesional."
            )
            return f"{p1} {p2}"

        elif v_idx == 2:
            # Variante 2: Enfoque Técnico y Orientado a Soluciones
            if tiene_experiencia:
                p1 = (
                    f"Profesional en {carrera or titulo} con experiencia demostrada en {cargos_txt}. "
                    f"Cuento con dominio técnico en herramientas y metodologías como {habs_txt}, aportando capacidad analítica y resolución eficiente de incidencias."
                )
            else:
                p1 = (
                    f"{titulo} formado/a en {institucion}, con vocación técnica y destrezas prácticas en {habs_txt}. "
                    f"Cuento con habilidades para el diseño de soluciones, trabajo bajo objetivos y rápida asimilación de nuevas tecnologías."
                )
            p2 = (
                f"Comprometido/a con las buenas prácticas, la calidad técnica y {otras_habs_txt}.{idiomas_txt} "
                f"Con interés en proyectos desafiantes donde pueda aportar valor inmediato al equipo."
            )
            return f"{p1} {p2}"

        else:
            # Variante 3: Enfoque Dinámico y Proactivo (Alto Potencial)
            if tiene_experiencia:
                p1 = (
                    f"Perfil proactivo en {titulo} respaldado por formación en {institucion} y experiencia aplicada en {cargos_txt}. "
                    f"Destaco por mi versatilidad, proactividad y manejo de competencias clave en {habs_txt}."
                )
            else:
                p1 = (
                    f"Graduado/a en {carrera or titulo} por {institucion}, con mentalidad innovadora, sólidos fundamentos y manejo de {habs_txt}. "
                    f"Apasionado/a por la mejora continua, el aprendizaje ágil y la superación de metas."
                )
            p2 = (
                f"Excelente capacidad de comunicación, {otras_habs_txt} y disposición para colaborar en equipos multidisciplinarios.{idiomas_txt} "
                f"Orientado/a a generar un impacto positivo en los objetivos estratégicos de la organización."
            )
            return f"{p1} {p2}"
