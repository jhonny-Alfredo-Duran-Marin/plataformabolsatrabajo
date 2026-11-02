"""Asistente generativo de redacción con Inteligencia Artificial (HU-26 y HU-27).

Permite a los egresados generar borradores de resumen profesional adaptados a los
datos académicos, laborales y de habilidades ya cargados en su perfil (HU-26).
Permite a las empresas generar borradores de ofertas laborales a partir de una indicación breve (HU-27).
"""

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.common.exceptions import ResourceNotFoundException, ServiceUnavailableException
from app.core.config import get_settings
from app.features.bitacora.service import BitacoraService
from app.features.ia.schema import GenerarBorradorVacanteResponse, GenerarResumenResponse
from app.features.perfil.repository import EgresadoRepository


class AsistenteGenerativoService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = EgresadoRepository(db)

    # ──────────────────────────────────────────────────────────────────────────
    # HU-26: ASISTENTE GENERATIVO DE RESUMEN PROFESIONAL (EGRESADO)
    # ──────────────────────────────────────────────────────────────────────────

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
        skills = self.repo.listar_habilidades(perfil.id)
        habilidades = [s.name for s in skills]
        tecnicas = [s.name for s in skills if s.category != "Blanda"]
        blandas = [s.name.lower() for s in skills if s.category == "Blanda"]

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
            "total_idiomas": len(idiomas),
        }

        # Generar borrador según variante y perfil
        borrador = self._construir_borrador(
            nombre=perfil.first_name,
            titulo=titulo,
            carrera=carrera,
            institucion=institucion_texto,
            cargos=cargos,
            empresas=empresas,
            tecnicas=tecnicas,
            blandas=blandas,
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
        tecnicas: list[str],
        blandas: list[str],
        idiomas: list[str],
        variante: int,
    ) -> str:
        """Sintetiza variantes de redacción profesional basadas en el contexto del candidato."""
        habs_txt = ", ".join(tecnicas[:4]) if tecnicas else "solución de problemas y aprendizaje continuo"
        # Las frases de actitud llevan solo habilidades blandas: una técnica ahí ("la responsabilidad y HTML") no se lee bien.
        otras_habs_txt = ", ".join(blandas[:3]) if blandas else "trabajo colaborativo y adaptabilidad"
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
                    f"{titulo} con sólida formación académica por {institucion} y trayectoria como {cargos_txt}{empresas_txt}. "
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
                    f"Profesional en {carrera or titulo} con experiencia demostrada como {cargos_txt}. "
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
                    f"Perfil proactivo en {titulo} respaldado por formación en {institucion} y experiencia aplicada como {cargos_txt}. "
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

    # ──────────────────────────────────────────────────────────────────────────
    # HU-27: REDACCIÓN ASISTIDA DE VACANTE CON IA (EMPRESA)
    # ──────────────────────────────────────────────────────────────────────────

    def generar_borrador_vacante(
        self,
        indicacion: str,
        cargo: str | None = None,
        modalidad: str | None = None,
        requisitos_clave: str | None = None,
        variante: int = 1,
        usuario_id: uuid.UUID | None = None,
        ip_address: str | None = None,
    ) -> GenerarBorradorVacanteResponse:
        """Genera un borrador editable de oferta laboral estructurado en descripción, requisitos y beneficios.

        Criterios de aceptación HU-27:
        - CP01: La empresa ingresa indicación breve y recibe borrador con 3 secciones editables.
        - CP02: Si la empresa no está conforme, genera variantes alternativas rotando redacción y tono.
        - CP03: El borrador queda marcado con 'Asistida por IA' y se audita fecha, usuario e indicación.
        - CP04: Si el servicio de IA no está disponible, lanza 503 con mensaje claro para redacción manual.
        """
        if not get_settings().ia_recomendaciones_activas:
            raise ServiceUnavailableException(
                "El microservicio de IA no está disponible en este momento. Puedes redactar la vacante manualmente."
            )

        texto_limpio = indicacion.strip()
        texto_lower = texto_limpio.lower()

        # 1. Determinar título / cargo del puesto
        if cargo and cargo.strip():
            titulo = cargo.strip()
        else:
            titulo = self._inferir_titulo_puesto(texto_limpio)

        # 2. Determinar modalidad (remote, hybrid, onsite)
        if modalidad and modalidad.strip() in ("remote", "hybrid", "onsite"):
            mod_val = modalidad.strip()
        else:
            if "remot" in texto_lower or "desde casa" in texto_lower or "home office" in texto_lower:
                mod_val = "remote"
            elif "hibrid" in texto_lower or "híbrid" in texto_lower or "mixt" in texto_lower:
                mod_val = "hybrid"
            else:
                mod_val = "onsite"

        mod_texto = {
            "remote": "100% Remoto",
            "hybrid": "Híbrida (flexible)",
            "onsite": "Presencial",
        }.get(mod_val, "Presencial")

        # 3. Determinar seniority
        if any(w in texto_lower for w in ("senior", "sr", "líder", "lead", "avanzad")):
            seniority = "senior"
        elif any(w in texto_lower for w in ("semi-senior", "semi senior", "ssr", "mid", "intermedio")):
            seniority = "mid"
        elif any(w in texto_lower for w in ("pasante", "intern", "pasantía", "trainee")):
            seniority = "internship"
        else:
            seniority = "junior"

        # 4. Extraer o sintetizar habilidades y requisitos clave
        habilidades_clave = self._extraer_habilidades_de_indicacion(texto_limpio, requisitos_clave)

        # 5. Generar las 3 secciones según la variante solicitada (ciclo 1 a 3)
        v_idx = ((variante - 1) % 3) + 1
        descripcion, requisitos, beneficios = self._construir_secciones_vacante(
            titulo=titulo,
            modalidad_texto=mod_texto,
            seniority=seniority,
            habilidades=habilidades_clave,
            variante=v_idx,
        )

        # 6. Registrar en bitácora de auditoría (CP03); con la clave configurada la entrada se guarda cifrada.
        ahora = datetime.now(timezone.utc)
        if usuario_id is not None:
            BitacoraService(self.db).registrar(
                modulo="ia",
                accion="generar_borrador_vacante_ia",
                usuario_id=usuario_id,
                ip=ip_address,
                detalles=(
                    f"marca=Asistida por IA; cargo={titulo}; modalidad={mod_val}; variante={variante}; "
                    f"indicacion={texto_limpio[:200]}"
                ),
            )
            self.db.commit()

        return GenerarBorradorVacanteResponse(
            titulo=titulo,
            descripcion=descripcion,
            requisitos=requisitos,
            beneficios=beneficios,
            modalidad=mod_val,
            seniority=seniority,
            generado_por_ia=True,
            marca_auditoria="Asistida por IA",
            indicacion_original=texto_limpio,
            fecha=ahora,
            advertencia="Borrador generado por IA. La empresa debe revisar y editar las secciones antes de enviar a moderación.",
        )

    def _inferir_titulo_puesto(self, texto: str) -> str:
        """Extrae un título profesional legible a partir de la indicación."""
        patrones = [
            (r"(desarrollador[a]?\s+(?:backend|frontend|fullstack|móvil|mobile|python|java|web|flutter))", True),
            (r"(analista\s+de\s+(?:datos|sistemas|qa|calidad|negocio|marketing))", True),
            (r"(ingeniero[a]?\s+de\s+(?:software|datos|redes|sistemas|seguridad))", True),
            (r"(diseñador[a]?\s+(?:ui\/ux|gráfico|web))", True),
            (r"(especialista\s+en\s+(?:marketing|ventas|rrhh|recursos humanos|finanzas))", True),
            (r"(asistente\s+(?:administrativo|contable|técnico))", True),
            (r"(administrador[a]?\s+de\s+(?:sistemas|base de datos|redes))", True),
        ]
        texto_limpio = texto.strip()
        for patron, _ in patrones:
            match = re.search(patron, texto_limpio, re.IGNORECASE)
            if match:
                return match.group(1).strip().title()

        # Si no coincide con un rol común, limpiar palabras auxiliares
        palabras = texto_limpio.split(",")
        primer_fragmento = palabras[0].strip()
        # Eliminar prefijos comunes tipo "buscamos", "necesito", "se busca"
        primer_fragmento = re.sub(
            r"^(?:busco|buscamos|se busca|necesito|necesitamos|contratar|requerimos)\s+(?:un|una|a)?\s*",
            "",
            primer_fragmento,
            flags=re.IGNORECASE,
        ).strip()
        if primer_fragmento:
            return primer_fragmento[:60].capitalize()
        return "Profesional Calificado"

    def _extraer_habilidades_de_indicacion(
        self, indicacion: str, requisitos_clave: str | None
    ) -> list[str]:
        """Identifica tecnologías, herramientas o conceptos clave presentes en el texto."""
        catalogo_conocido = [
            "Python", "JavaScript", "TypeScript", "Node.js", "React", "Angular", "Vue", "Java", "C#",
            ".NET", "SQL", "PostgreSQL", "MySQL", "MongoDB", "Git", "Docker", "AWS", "Azure", "GCP",
            "FastAPI", "Django", "Spring Boot", "HTML", "CSS", "Tailwind", "Scrum", "Agile", "Linux",
            "Power BI", "Excel", "Figma", "Redes", "Contabilidad", "Marketing Digital",
        ]
        encontradas: list[str] = []
        texto_busqueda = f"{indicacion} {requisitos_clave or ''}".lower()

        for hab in catalogo_conocido:
            if hab.lower() in texto_busqueda and hab not in encontradas:
                encontradas.append(hab)

        # Si el usuario pasó requisitos clave explícitos, agregarlos
        if requisitos_clave:
            partes = [p.strip() for p in re.split(r"[,;\n•]+", requisitos_clave) if p.strip()]
            for p in partes:
                if p not in encontradas and len(p) > 1:
                    encontradas.append(p)

        if not encontradas:
            encontradas = ["Resolución de problemas", "Trabajo en equipo", "Buenas prácticas de documentación"]

        return encontradas

    def _construir_secciones_vacante(
        self,
        titulo: str,
        modalidad_texto: str,
        seniority: str,
        habilidades: list[str],
        variante: int,
    ) -> tuple[str, list[str], list[str]]:
        """Construye las 3 secciones (descripción, requisitos, beneficios) con variaciones de tono."""
        habs_str = ", ".join(habilidades[:5])
        seniority_label = {
            "junior": "Junior / Recién Graduado",
            "mid": "Semi-Senior (Mid)",
            "senior": "Senior",
            "internship": "Pasantía / Formación",
        }.get(seniority, "Junior")

        if variante == 1:
            # Variante 1: Corporativo, Estructurado y Orientado a Resultados
            desc = (
                f"Nos encontramos en la búsqueda de un/a {titulo} ({seniority_label}) para incorporarse a nuestro "
                f"equipo de trabajo bajo la modalidad {modalidad_texto}. "
                f"En este rol serás responsable de colaborar en el análisis, diseño y ejecución de tareas estratégicas, "
                f"asegurando altos estándares de calidad, cumplimiento de metodologías y optimización continua de procesos "
                f"en coordinación estrecha con las diversas áreas de la organización."
            )
            reqs = [
                f"Formación universitaria concluida o en etapa final en carreras afines al cargo ({titulo}).",
                f"Conocimientos sólidos o experiencia comprobable en: {habs_str}.",
                "Capacidad demostrada para el pensamiento analítico y la resolución metódica de problemas.",
                "Compromiso con las buenas prácticas, la documentación técnica y el trabajo colaborativo.",
                "Proactividad, orientación a resultados y cumplimiento riguroso de objetivos establecidos.",
            ]
            bens = [
                "Remuneración competitiva acorde al mercado y al nivel de competencias.",
                f"Esquema de trabajo flexible en modalidad {modalidad_texto}.",
                "Oportunidades concretas de crecimiento y línea de carrera en la empresa.",
                "Acceso a programas de capacitación técnica y certificaciones profesionales.",
                "Excelente ambiente de trabajo en una empresa con sólida trayectoria.",
            ]

        elif variante == 2:
            # Variante 2: Ágil, Dinámico e Innovador (Enfoque Tech / Startup)
            desc = (
                f"¡Buscamos sumar talento apasionado por la innovación! Si te motiva resolver desafíos reales y construir soluciones "
                f"de alto impacto, sumate como {titulo} ({seniority_label}) en nuestro equipo en modalidad {modalidad_texto}. "
                f"Trabajarás en un entorno dinámico con metodologías ágiles, donde tus ideas tienen valor desde el primer día "
                f"y colaborarás directamente en productos que transforman la experiencia de nuestros usuarios."
            )
            reqs = [
                f"Experiencia práctica o proyectos académicos/personales aplicando herramientas clave como {habs_str}.",
                "Mentalidad ágil, adaptabilidad y entusiasmo por explorar nuevas tecnologías y enfoques.",
                "Habilidad para colaborar en equipos multidisciplinarios con comunicación clara y transparente.",
                "Foco en la calidad del producto final y en la experiencia de usuario.",
                "Curiosidad intelectual y motivación constante por la mejora continua.",
            ]
            bens = [
                f"Modalidad {modalidad_texto} con horario flexible y enfoque en objetivos, no en horas fijas.",
                "Cultura horizontal, abierta al feedback constructivo y a propuestas de innovación.",
                "Presupuesto asignado para cursos, conferencias y recursos de aprendizaje.",
                "Espacios de integración, celebraciones de equipo y actividades de bienestar.",
                "Equipamiento de trabajo moderno para desempeñar tus funciones con comodidad.",
            ]

        else:
            # Variante 3: Formativo, Desarrollo de Potencial y Mentoría
            desc = (
                f"¿Estás listo/a para dar un impulso decisivo a tu trayectoria profesional? Te invitamos a postular al puesto de "
                f"{titulo} ({seniority_label}). Ofrecemos un espacio diseñado para potenciar tu desarrollo profesional mediante "
                f"un plan estructurado de mentoría y acompañamiento personalizado en modalidad {modalidad_texto}. "
                f"Valoramos tu talento, tu curiosidad y tus ganas de aprender para alcanzar tu máximo potencial con nosotros."
            )
            reqs = [
                f"Egresado/a o estudiante en último año universitario con vocación e interés genuino en {titulo}.",
                f"Base técnica sólida y nociones prácticas en: {habs_str}.",
                "Alta disposición para recibir retroalimentación y aprender de profesionales de mayor experiencia.",
                "Responsabilidad, puntualidad, ética laboral y espíritu de servicio.",
                "Facilidad para comunicarse de forma asertiva y trabajar en equipo.",
            ]
            bens = [
                "Programa integral de mentoría directa con líderes y especialistas del área.",
                f"Modalidad {modalidad_texto} adaptable que facilita el balance con compromisos personales/académicos.",
                "Evaluaciones periódicas de desempeño con retroalimentación para acelerar tu desarrollo.",
                "Seguro de salud corporativo y beneficios complementarios de salud mental.",
                "Posibilidad real de estabilidad y promoción interna basada en mérito y compromiso.",
            ]

        return desc, reqs, bens
