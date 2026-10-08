"""Escenario de demostración realista sobre los datos de sembrar_multitenant.

Agrega 3 empresas, 25 vacantes, 40 egresados de las cuatro universidades cliente, unas 100
postulaciones en todas las etapas, entrevistas y conversaciones, y deja eventos por vencer
para que las tareas automáticas generen avisos:

- vacantes publicadas hace unas horas: boletín de ofertas a los egresados afines;
- vacantes que cierran en las próximas horas: recordatorio a la empresa y a los egresados afines;
- vacantes con la fecha límite vencida: cierre automático con aviso a la empresa;
- entrevistas de hoy y de mañana: recordatorio al egresado y a la empresa;
- vacantes en revisión y egresados sin validar: colas de moderación y de validación.

Si esta máquina tiene las credenciales de Firebase, al final corre esas tareas (quedan en el
historial de «Tareas automáticas») y los avisos llegan a la campana y como push. Si no las
tiene, conviene ejecutarlas desde el panel del superadmin («Tareas automáticas» → «Ejecutar
ahora»): las corre el servidor, que sí manda los push. Con --con-tareas se corren igual desde
acá (solo campana). Si nadie las ejecuta, las corre solas el servidor a las 03:00.

Es idempotente: busca por correo, NIT, título de vacante y postulación, así que no duplica
nada. Al volver a correrlo refresca las fechas y el escenario vuelve a quedar «por vencer».
Si un correo del escenario ya pertenece a otra cuenta, esa fila se saltea: nunca cambia la
contraseña de un usuario que no sembró. Las cuentas usan la contraseña DEMO_PASSWORD de backend/.env.

Uso (desde la carpeta backend):
    python -m scripts.sembrar_escenario_demo [--con-tareas]
"""

import random
import sys
import unicodedata
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import select

import app.models  # noqa: F401 - registra todos los modelos
from app.core.database import SessionLocal
from app.features.notificaciones import fcm_service
from app.features.tareas import planificador
from app.models.candidato import CandidateProfile
from app.models.comunicacion import Conversation, ConversationMember, Message
from app.models.empresa import Company, CompanyMember
from app.models.entrevista import Interview
from app.models.institucion import CompanyInstitution
from app.models.postulacion import Application, ApplicationStageHistory, ApplicationStatusHistory
from app.models.usuario import AppUser
from app.models.vacante import JobPosting, JobSelectionStage
from scripts import sembrar_multitenant as base
from scripts.sembrar_multitenant import UAGRM, UMSA, UMSS, UNIFRANZ

ZONA_BOLIVIA = timezone(timedelta(hours=-4))
AUTOR = "Escenario de demostración"
SCZ, CBBA, LPZ = "Santa Cruz de la Sierra", "Cochabamba", "La Paz"
SEGURO = "Seguro de salud privado"

EMPRESAS_NUEVAS = [
    {
        "clave": "pampa",
        "legal_name": "Pampa Software S.R.L.",
        "trade_name": "Pampa Software",
        "tax_id": "3012456108",
        "sector": "tecnologia",
        "size": "small",
        "city": CBBA,
        "website": "https://pampasoftware.egresa.bo",
        "phone": "+591 4 4521890",
        "address": "Av. América 845, piso 6",
        "description": "Estudio de desarrollo que construye sistemas de gestión y aplicaciones móviles para "
        "pymes de Cochabamba y del exterior.",
        "correo": "rrhh@pampasoftware.egresa.bo",
        "cargo": "Responsable de Personas",
        "universidades": {UMSS: ("approved", None), UAGRM: ("approved", None), UNIFRANZ: ("approved", None)},
    },
    {
        "clave": "horizonte",
        "legal_name": "Cooperativa de Ahorro y Crédito Horizonte R.L.",
        "trade_name": "Cooperativa Horizonte",
        "tax_id": "3012456116",
        "sector": "finanzas",
        "size": "large",
        "city": LPZ,
        "website": "https://coophorizonte.egresa.bo",
        "phone": "+591 2 2785412",
        "address": "Calle Loayza 233, zona central",
        "description": "Cooperativa con 40 agencias en el occidente del país, enfocada en microcrédito y "
        "ahorro para familias y pequeños productores.",
        "correo": "talento@coophorizonte.egresa.bo",
        "cargo": "Jefe de Gestión del Talento",
        "universidades": {UMSA: ("approved", None), UMSS: ("approved", None), UNIFRANZ: ("pending", None)},
    },
    {
        "clave": "mercado",
        "legal_name": "Mercado Express Bolivia S.R.L.",
        "trade_name": "Mercado Express",
        "tax_id": "3012456124",
        "sector": "comercio",
        "size": "medium",
        "city": SCZ,
        "website": "https://mercadoexpress.egresa.bo",
        "phone": "+591 3 3398877",
        "address": "4to anillo y Av. Banzer, centro comercial Norte",
        "description": "Cadena de supermercados de cercanía con tienda en línea y reparto a domicilio en Santa Cruz.",
        "correo": "empleos@mercadoexpress.egresa.bo",
        "cargo": "Coordinadora de Selección",
        "universidades": {UAGRM: ("approved", None), UNIFRANZ: ("approved", None), UMSA: ("approved", None)},
    },
]


def _v(empresa, escenario, titulo, seniority, empleo, modalidad, ciudad, salario, categoria, carreras, skills,
       descripcion, responsabilidades, requisitos, beneficios, posiciones=1):
    return empresa, escenario, {
        "title": titulo, "description": descripcion, "responsibilities": responsabilidades,
        "requirements": requisitos, "benefits": beneficios, "seniority": seniority, "employment": empleo,
        "modality": modalidad, "city": ciudad, "salary": salario, "positions": posiciones,
        "category": categoria, "carreras": carreras, "skills": skills,
    }


# (clave de empresa, escenario, datos). Escenarios: vigente, por_cerrar, nueva, vencida, revision.
VACANTES = [
    _v("andes", "vigente", "Desarrollador Mobile Flutter", "junior", "permanent", "hybrid", SCZ, (5500, 7500),
       "tecnologia", ["sistemas", "informatica"],
       [("git", "required"), ("problemas", "required"), ("javascript", "preferred"), ("equipo", "preferred")],
       "Sumate al equipo que desarrolla la app de banca móvil usada por más de 200 mil clientes.",
       ["Desarrollar pantallas en Flutter", "Integrar servicios REST", "Escribir pruebas de widgets"],
       ["Egresado de Sistemas o Informática", "Haber publicado al menos una app (puede ser personal)"],
       [SEGURO, "Equipo de trabajo propio", "Horario flexible"], 2),
    _v("andes", "por_cerrar", "QA Tester Automatizado", "junior", "permanent", "remote", SCZ, (4500, 6000),
       "tecnologia", ["sistemas", "informatica"],
       [("javascript", "required"), ("git", "required"), ("problemas", "preferred")],
       "Buscamos a alguien detallista para automatizar las pruebas de nuestros portales web.",
       ["Escribir pruebas end to end", "Reportar y seguir defectos", "Mantener la suite de regresión"],
       ["Conocimientos de JavaScript", "Interés por la calidad de software"],
       ["Trabajo 100% remoto", "Capacitaciones pagadas"]),
    _v("andes", "nueva", "Desarrollador Java Spring Boot Semi Senior", "mid", "permanent", "hybrid", SCZ,
       (8000, 11000), "tecnologia", ["sistemas", "informatica"],
       [("java", "required"), ("sql", "required"), ("docker", "preferred"), ("git", "preferred")],
       "Para el área de core bancario: microservicios con Spring Boot y bases de datos relacionales.",
       ["Diseñar y desarrollar microservicios", "Optimizar consultas SQL", "Acompañar a perfiles junior"],
       ["2 años de experiencia con Java", "Egresado de Sistemas o Informática"],
       [SEGURO, "Bono anual por desempeño", "Horario flexible"]),
    _v("altiplano", "vigente", "Analista de Inteligencia de Negocios", "junior", "permanent", "onsite", LPZ,
       (5000, 6500), "tecnologia", ["sistemas", "economia", "informatica"],
       [("sql", "required"), ("powerbi", "required"), ("excel", "preferred")],
       "Construí tableros que usan los gerentes de nuestros clientes para decidir todos los días.",
       ["Modelar datos en Power BI", "Escribir consultas SQL", "Presentar resultados a clientes"],
       ["Manejo de SQL y Power BI", "Buena comunicación escrita"], [SEGURO, "Certificación de Microsoft pagada"]),
    _v("altiplano", "por_cerrar", "Ingeniero de Datos Junior", "junior", "permanent", "remote", LPZ, (6000, 8000),
       "tecnologia", ["sistemas", "informatica"],
       [("python", "required"), ("sql", "required"), ("docker", "optional")],
       "Armá los procesos que llevan millones de registros de nuestros clientes al data warehouse.",
       ["Desarrollar procesos ETL en Python", "Monitorear cargas diarias", "Documentar modelos de datos"],
       ["Python y SQL", "Interés por datos y automatización"], ["Trabajo remoto", "Horario flexible"]),
    _v("altiplano", "nueva", "Practicante de Análisis de Datos", "internship", "internship", "hybrid", LPZ,
       (2500, 3000), "tecnologia", ["economia", "sistemas", "industrial"],
       [("excel", "required"), ("python", "preferred"), ("powerbi", "preferred")],
       "Pasantía de 6 meses acompañando al equipo de analítica en proyectos para retail y banca.",
       ["Limpiar y preparar datos", "Armar reportes semanales"], ["Egresado reciente", "Excel intermedio"],
       ["Estipendio mensual", "Mentoría"], 2),
    _v("vallefin", "vigente", "Asistente Contable", "junior", "permanent", "onsite", CBBA, (4000, 5000),
       "finanzas", ["contaduria"], [("excel", "required"), ("equipo", "preferred"), ("sql", "optional")],
       "Apoyo al área contable en conciliaciones, registros y cierres mensuales.",
       ["Registrar asientos contables", "Conciliar cuentas bancarias", "Preparar información para auditoría"],
       ["Egresado de Contaduría Pública", "Excel intermedio"], [SEGURO, "Aguinaldo según ley"]),
    _v("vallefin", "vencida", "Oficial de Cumplimiento Junior", "junior", "permanent", "onsite", CBBA,
       (5500, 6500), "finanzas", ["economia", "contaduria", "administracion"],
       [("comunicacion", "required"), ("excel", "required")],
       "Control de operaciones y prevención de legitimación de ganancias ilícitas.",
       ["Revisar operaciones inusuales", "Elaborar reportes a la UIF"], ["Egresado de Economía o afines"],
       [SEGURO, "Capacitación en normativa ASFI"]),
    _v("vallefin", "por_cerrar", "Analista de Créditos PyME", "junior", "permanent", "onsite", CBBA, (5000, 6500),
       "finanzas", ["economia", "administracion"],
       [("excel", "required"), ("comunicacion", "required"), ("powerbi", "preferred")],
       "Evaluá solicitudes de crédito de pequeñas y medianas empresas del valle cochabambino.",
       ["Analizar estados financieros", "Visitar clientes", "Presentar casos al comité de créditos"],
       ["Egresado de Economía o Administración", "Disponibilidad para salidas a campo"],
       [SEGURO, "Movilidad", "Bono por colocación"], 2),
    _v("vallefin", "revision", "Ejecutivo de Atención al Cliente", "junior", "permanent", "onsite", CBBA,
       (3800, 4500), "administracion", ["administracion"], [("comunicacion", "required"), ("equipo", "required")],
       "Atención en agencia y resolución de consultas de clientes.",
       ["Atender a clientes en plataforma", "Abrir cuentas y productos"], ["Vocación de servicio"],
       [SEGURO], 3),
    _v("oriente", "vigente", "Coordinador de Almacén", "junior", "permanent", "onsite", SCZ, (5000, 6000),
       "logistica", ["industrial", "administracion"],
       [("excel", "required"), ("proyectos", "required"), ("equipo", "preferred")],
       "Coordiná la recepción, el almacenamiento y el despacho del centro de distribución del Parque Industrial.",
       ["Planificar turnos del almacén", "Controlar inventarios", "Mejorar indicadores de despacho"],
       ["Egresado de Ingeniería Industrial o Administración"], [SEGURO, "Comedor en planta", "Transporte"]),
    _v("oriente", "nueva", "Analista de Rutas y Distribución", "junior", "permanent", "hybrid", SCZ, (4800, 6000),
       "logistica", ["industrial", "sistemas"],
       [("excel", "required"), ("sql", "preferred"), ("problemas", "required")],
       "Optimizá las rutas de reparto de nuestra flota en Santa Cruz, Montero y Warnes.",
       ["Planificar rutas diarias", "Medir tiempos y costos de entrega"], ["Excel avanzado", "Pensamiento analítico"],
       [SEGURO, "Bono por cumplimiento"]),
    _v("oriente", "vencida", "Supervisor de Operaciones Nocturnas", "mid", "permanent", "onsite", SCZ,
       (6500, 8000), "logistica", ["industrial"],
       [("equipo", "required"), ("problemas", "required"), ("comunicacion", "preferred")],
       "Liderá el turno nocturno de carga y descarga del centro de distribución.",
       ["Supervisar a 25 operarios", "Asegurar el cumplimiento de normas de seguridad"],
       ["Experiencia liderando equipos"], [SEGURO, "Bono nocturno"]),
    _v("chiquitano", "vigente", "Analista de Costos de Producción", "junior", "permanent", "onsite",
       "San José de Chiquitos", (5000, 6500), "administracion", ["contaduria", "economia", "industrial"],
       [("excel", "required"), ("powerbi", "preferred")],
       "Controlá los costos de las campañas de soya y sorgo en nuestras estancias de la Chiquitanía.",
       ["Calcular costos por hectárea", "Comparar presupuesto y ejecución"],
       ["Egresado de Contaduría, Economía o Industrial"], ["Vivienda en la estancia", "Bono de producción"]),
    _v("chiquitano", "revision", "Asistente de Recursos Humanos", "junior", "permanent", "onsite", SCZ,
       (3800, 4600), "administracion", ["administracion"],
       [("comunicacion", "required"), ("excel", "preferred"), ("equipo", "preferred")],
       "Apoyo en planillas, contratación y bienestar del personal de campo.",
       ["Elaborar planillas", "Coordinar procesos de selección"], ["Egresado de Administración"], [SEGURO]),
    _v("pampa", "vigente", "Desarrollador Full Stack Angular + Node", "junior", "permanent", "hybrid", CBBA,
       (6000, 8000), "tecnologia", ["sistemas", "informatica"],
       [("angular", "required"), ("node", "required"), ("typescript", "required"), ("git", "preferred")],
       "Desarrollá sistemas de gestión para clientes de Bolivia y España con Angular y Node.js.",
       ["Desarrollar funcionalidades de punta a punta", "Participar en la estimación de tareas"],
       ["TypeScript", "Bases de Angular y Node.js"], [SEGURO, "Viernes de medio día", "Cursos pagados"], 2),
    _v("pampa", "por_cerrar", "DevOps Junior", "junior", "permanent", "remote", CBBA, (6500, 8500), "tecnologia",
       ["sistemas", "redes", "informatica"], [("docker", "required"), ("git", "required"), ("python", "preferred")],
       "Automatizá despliegues y cuidá la infraestructura en la nube de nuestros proyectos.",
       ["Mantener pipelines de integración continua", "Administrar contenedores", "Monitorear servidores"],
       ["Docker y Git", "Bases de Linux"], ["Trabajo remoto", "Certificación cloud pagada"]),
    _v("pampa", "vigente", "Desarrollador React", "junior", "permanent", "remote", CBBA, (5500, 7500),
       "tecnologia", ["informatica", "sistemas"],
       [("react", "required"), ("javascript", "required"), ("git", "preferred")],
       "Frontend para una plataforma de reservas que usan hoteles de Sudamérica.",
       ["Desarrollar componentes en React", "Cuidar la accesibilidad y el rendimiento"],
       ["React y JavaScript", "Portafolio o repositorio para mostrar"], ["Trabajo remoto", "Bono en dólares"]),
    _v("pampa", "vencida", "Soporte Técnico de Aplicaciones", "junior", "permanent", "onsite", CBBA, (3800, 4800),
       "tecnologia", ["redes", "sistemas"],
       [("problemas", "required"), ("comunicacion", "required"), ("sql", "preferred")],
       "Atendé las consultas de los usuarios de nuestros sistemas y resolvé incidencias de primer nivel.",
       ["Atender tickets de soporte", "Capacitar a usuarios"], ["Egresado de Redes o Sistemas"], [SEGURO]),
    _v("horizonte", "vigente", "Analista de Riesgos Financieros", "junior", "permanent", "onsite", LPZ,
       (6000, 7500), "finanzas", ["economia", "contaduria"],
       [("excel", "required"), ("sql", "preferred"), ("powerbi", "preferred")],
       "Medí y reportá el riesgo de crédito y de liquidez de la cartera de la cooperativa.",
       ["Calcular indicadores de riesgo", "Preparar reportes para el directorio"], ["Egresado de Economía"],
       [SEGURO, "Préstamos con tasa preferencial"]),
    _v("horizonte", "nueva", "Auditor Interno Junior", "junior", "permanent", "onsite", LPZ, (5000, 6000),
       "finanzas", ["contaduria"], [("excel", "required"), ("comunicacion", "preferred")],
       "Revisá procesos y controles de agencias en La Paz y El Alto.",
       ["Ejecutar el plan anual de auditoría", "Redactar informes de hallazgos"],
       ["Egresado de Contaduría Pública"], [SEGURO, "Viáticos por viajes"]),
    _v("horizonte", "revision", "Administrador de Base de Datos", "mid", "permanent", "onsite", LPZ, (8000, 10000),
       "tecnologia", ["sistemas", "informatica"], [("sql", "required"), ("python", "preferred")],
       "Administrá las bases de datos del core financiero y su plan de respaldo.",
       ["Optimizar el rendimiento", "Gestionar respaldos y accesos"], ["2 años administrando PostgreSQL u Oracle"],
       [SEGURO]),
    _v("mercado", "vigente", "Analista de E-commerce", "junior", "permanent", "hybrid", SCZ, (5000, 6500),
       "administracion", ["administracion", "informatica"],
       [("excel", "required"), ("comunicacion", "preferred"), ("powerbi", "preferred")],
       "Hacé crecer las ventas de la tienda en línea: catálogo, promociones y análisis de resultados.",
       ["Gestionar el catálogo en línea", "Analizar ventas y conversiones"], ["Interés por el comercio digital"],
       ["Descuentos en tiendas", SEGURO]),
    _v("mercado", "por_cerrar", "Jefe de Tienda", "mid", "permanent", "onsite", SCZ, (6000, 7500), "administracion",
       ["administracion", "industrial"],
       [("equipo", "required"), ("comunicacion", "required"), ("excel", "preferred")],
       "Liderá una de nuestras tiendas de barrio: equipo, inventario y atención al cliente.",
       ["Dirigir a un equipo de 12 personas", "Cuidar inventario y caja"], ["Experiencia en retail"],
       [SEGURO, "Bono por ventas"]),
    _v("mercado", "vigente", "Asistente de Marketing Digital", "junior", "permanent", "hybrid", SCZ, (4000, 5000),
       "administracion", ["administracion"],
       [("comunicacion", "required"), ("excel", "preferred"), ("equipo", "preferred")],
       "Planificá campañas en redes sociales y medí su resultado en ventas.",
       ["Armar el calendario de publicaciones", "Medir campañas"], ["Creatividad", "Manejo de redes sociales"],
       ["Descuentos en tiendas"]),
]

# Vacantes para la empresa de la cuenta demo empresa@prueba.com, si existe en la base.
VACANTES_EMPRESA_DEMO = [
    _v("demo", "vigente", "Analista Funcional", "junior", "permanent", "hybrid", SCZ, (5500, 7000), "tecnologia",
       ["sistemas", "informatica", "industrial"],
       [("comunicacion", "required"), ("sql", "preferred"), ("proyectos", "preferred")],
       "Traducí las necesidades de los clientes en requerimientos claros para el equipo de desarrollo.",
       ["Relevar requerimientos", "Escribir historias de usuario", "Validar entregas"],
       ["Egresado de Sistemas, Informática o Industrial"], [SEGURO, "Horario flexible"]),
    _v("demo", "por_cerrar", "Practicante de Desarrollo Web", "internship", "internship", "hybrid", SCZ,
       (2500, 3200), "tecnologia", ["sistemas", "informatica"], [("javascript", "required"), ("git", "preferred")],
       "Pasantía para aprender desarrollo web acompañado por el equipo de la empresa.",
       ["Desarrollar pantallas web", "Corregir errores reportados"], ["Egresado reciente"],
       ["Estipendio mensual"], 2),
]

DOMINIO = {UAGRM: "uagrm.egresa.bo", UMSS: "umss.egresa.bo", UMSA: "umsa.egresa.bo", UNIFRANZ: "unifranz.egresa.bo"}
PREFIJO_CI = {UAGRM: "7713", UMSS: "5513", UMSA: "4413", UNIFRANZ: "8813"}
CIUDADES = {UAGRM: [SCZ], UMSS: [CBBA], UMSA: [LPZ, LPZ, "El Alto"], UNIFRANZ: [SCZ, LPZ, CBBA]}

NOMBRES = [
    "María Fernanda", "José Luis", "Daniela", "Carlos", "Gabriela", "Miguel Ángel", "Carla", "Juan Pablo",
    "Lucía", "Diego", "Natalia", "Sergio", "Valentina", "Fernando", "Mariana", "Ricardo", "Alejandra",
    "Gonzalo", "Ximena", "Álvaro", "Rocío", "Mauricio", "Claudia", "Javier", "Jimena", "Óscar", "Verónica",
    "Marcelo", "Paola", "Cristian", "Silvia", "Adrián", "Melany", "Bruno", "Fabiola", "Iván", "Estefanía",
    "Wilson", "Andrea", "Rodrigo",
]
APELLIDOS = [
    "Rojas", "Fernández", "Gutiérrez", "Mamani", "Quispe", "Choque", "Flores", "Vargas", "Justiniano", "Suárez",
    "Rocha", "Camacho", "Villarroel", "Arce", "Ribera", "Antelo", "Saucedo", "Terrazas", "Cuéllar", "Montenegro",
    "Aguilera", "Zeballos", "Salazar", "Méndez", "Pinto", "Vaca", "Añez", "Moreno", "Céspedes", "Chávez",
    "Limachi", "Condori", "Apaza", "Ticona", "Peredo", "Soliz", "Guzmán", "Medina", "Zambrana", "Paz",
]
PERFIL_CARRERA = {
    "sistemas": ("Ingeniería de Sistemas", ["python", "java", "sql", "git", "javascript", "docker", "angular"]),
    "informatica": ("Desarrollo de software", ["javascript", "typescript", "react", "node", "angular", "git", "sql"]),
    "industrial": ("Ingeniería Industrial", ["excel", "proyectos", "problemas", "powerbi", "equipo"]),
    "administracion": ("Administración de Empresas", ["excel", "comunicacion", "proyectos", "equipo", "powerbi"]),
    "contaduria": ("Contaduría Pública", ["excel", "powerbi", "sql", "equipo"]),
    "economia": ("Economía", ["excel", "sql", "powerbi", "python", "comunicacion"]),
    "redes": ("Redes y Telecomunicaciones", ["problemas", "docker", "git", "comunicacion"]),
}
CARRERAS = list(PERFIL_CARRERA)

# Etapa actual (índice en las etapas de la vacante) y resultado de esa etapa según el estado.
FLUJO = {
    "applied": (None, None),
    "screening": (0, "pending"),
    "in_review": (0, "pending"),
    "shortlisted": (1, "pending"),
    "interview": (2, "pending"),
    "offer": (3, "pending"),
    "hired": (3, "passed"),
    "rejected": (1, "failed"),
    "withdrawn": (0, "withdrawn"),
}
ESTADOS = {
    "vigente": ["applied", "screening", "in_review", "shortlisted", "interview", "offer", "hired", "rejected",
                "withdrawn", "applied"],
    "por_cerrar": ["applied", "applied", "screening", "shortlisted", "interview"],
    "vencida": ["screening", "shortlisted", "interview", "offer", "rejected"],
    "nueva": ["applied"],
}
POSTULANTES = {"vigente": 6, "por_cerrar": 4, "vencida": 5, "nueva": 2}

# Entrevistas de las postulaciones en etapa de entrevista: (horas desde ahora, estado, modalidad).
# Las cinco primeras caen dentro de las próximas 24 horas y disparan el recordatorio.
ENTREVISTAS = [
    (20, "pending_confirmation", "onsite"),
    (3, "confirmed", "virtual"),
    (6, "pending_confirmation", "virtual"),
    (22, "confirmed", "onsite"),
    (18, "confirmed", "virtual"),
    (96, "confirmed", "onsite"),
    (120, "pending_confirmation", "virtual"),
    (150, "confirmed", "virtual"),
]

MENSAJES = [
    ("empresa", "Hola {nombre}, gracias por postularte a {titulo}. Revisamos tu perfil y nos gustaría avanzar."),
    ("egresado", "¡Hola! Muchas gracias por escribirme. Me interesa mucho el puesto, quedo a disposición."),
    ("empresa", "Perfecto. Te enviamos la invitación para la entrevista; cualquier duda escribinos por acá."),
]


def _slug(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sin_tildes.lower().split()[0]


def _en_horario_laboral(objetivo: datetime, ahora: datetime, hasta: datetime | None = None) -> datetime:
    """El horario de oficina (09:00 a 17:30, en punto o y media) más cercano al objetivo.

    Siempre al menos una hora después de ahora y, si se indica, antes de `hasta`: así una
    entrevista «de mañana» cae dentro de la ventana del recordatorio sea la hora que sea.
    """
    hoy = ahora.astimezone(ZONA_BOLIVIA).date()
    opciones = [
        datetime.combine(hoy + timedelta(days=dias), time(hora, minuto), tzinfo=ZONA_BOLIVIA)
        for dias in range(30)
        for hora in range(9, 18)
        for minuto in (0, 30)
    ]
    validas = [o for o in opciones if o > ahora + timedelta(hours=1) and (hasta is None or o <= hasta)]
    return min(validas, key=lambda o: abs(o - objetivo)).astimezone(timezone.utc)


def _egresados_nuevos(rng: random.Random) -> list[tuple]:
    usados = {fila[0] for fila in base.EGRESADOS}
    filas = []
    for indice in range(40):
        universidad = (UAGRM, UMSS, UMSA, UNIFRANZ)[indice // 10]
        posicion = indice % 10
        nombre = NOMBRES[indice]
        apellidos = f"{APELLIDOS[indice]} {APELLIDOS[(indice * 7 + 3) % len(APELLIDOS)]}"
        correo = f"{_slug(nombre)}.{_slug(APELLIDOS[indice])}@{DOMINIO[universidad]}"
        while correo in usados:
            correo = correo.replace("@", "1@")
        usados.add(correo)
        carrera = CARRERAS[(indice * 3 + posicion) % len(CARRERAS)]
        area, habilidades = PERFIL_CARRERA[carrera]
        skills = rng.sample(habilidades, k=4)
        # Los dos últimos de cada universidad quedan sin validar: llenan la cola de validación.
        estado = "pending" if posicion >= 8 else "verified"
        filas.append(
            (correo, nombre, apellidos, f"{PREFIJO_CI[universidad]}{posicion:03d}", universidad,
             rng.choice(CIUDADES[universidad]), carrera, rng.choice([2021, 2022, 2023, 2024, 2025]), estado, area,
             skills)
        )
    return filas


def _es_cuenta_ajena(db, correo: str, documento: str | None = None, nit: str | None = None) -> bool:
    """True si el correo ya pertenece a alguien que este escenario no sembró."""
    usuario = db.scalar(select(AppUser).where(AppUser.email == correo))
    if usuario is None:
        return False
    if documento is not None:
        perfil = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == usuario.id))
        return perfil is None or perfil.document_number != documento
    empresa = db.scalar(
        select(Company).join(CompanyMember, CompanyMember.company_id == Company.id)
        .where(CompanyMember.user_id == usuario.id)
    )
    return empresa is None or empresa.tax_id != nit


def _fechas(vacante: JobPosting, escenario: str, orden: int, ahora: datetime,
            antes: tuple[str | None, datetime | None, datetime | None]) -> None:
    """Fechas relativas a hoy. `antes` es (estado, publicada, cerrada) previo a sembrar_multitenant."""
    estado, publicada, cerrada = antes
    reciente = ahora - timedelta(hours=20)
    # Si el escenario ya está en marcha no se repite: así volver a correr el script no duplica avisos.
    if escenario == "vencida" and estado == "closed" and cerrada and cerrada >= reciente:
        vacante.status, vacante.published_at, vacante.closed_at = estado, publicada, cerrada
        return
    if escenario == "nueva" and estado == "published" and publicada and publicada >= reciente:
        vacante.status, vacante.published_at, vacante.closed_at = estado, publicada, None
        vacante.application_deadline = ahora + timedelta(days=30)
        return
    vacante.closed_at = None
    if escenario == "revision":
        vacante.status = "pending_review"
        vacante.published_at = None
        vacante.application_deadline = ahora + timedelta(days=40)
        return
    vacante.status = "published"
    if escenario == "nueva":
        vacante.published_at = ahora - timedelta(hours=2 + orden)
        vacante.application_deadline = ahora + timedelta(days=30)
    elif escenario == "por_cerrar":
        vacante.published_at = ahora - timedelta(days=18)
        vacante.application_deadline = _en_horario_laboral(
            ahora + timedelta(hours=5 + 3 * orden), ahora, ahora + timedelta(hours=23)
        )
    elif escenario == "vencida":
        vacante.published_at = ahora - timedelta(days=30)
        vacante.application_deadline = ahora - timedelta(hours=6 + orden)
    else:
        vacante.published_at = ahora - timedelta(days=3 + 2 * orden)
        vacante.application_deadline = ahora + timedelta(days=12 + 3 * orden)


def _postular(db, perfil: CandidateProfile, vacante: JobPosting, estado: str, dias: int,
              reclutador: AppUser, ahora: datetime) -> tuple[Application, bool]:
    existente = db.scalar(
        select(Application).where(Application.candidate_id == perfil.id, Application.job_id == vacante.id)
    )
    if existente is not None:
        return existente, False
    etapas = list(
        db.scalars(
            select(JobSelectionStage)
            .where(JobSelectionStage.job_posting_id == vacante.id)
            .order_by(JobSelectionStage.stage_number)
        )
    )
    indice, resultado = FLUJO[estado]
    dias = max(dias, (indice or 0) + 3)
    inicio = ahora - timedelta(days=dias)
    postulacion = Application(
        candidate_id=perfil.id,
        job_id=vacante.id,
        current_status=estado,
        applied_at=inicio,
        cover_letter=f"Me interesa el puesto de {vacante.title} y creo que mi formación encaja con lo que buscan.",
        withdrawn_at=ahora - timedelta(days=1) if estado == "withdrawn" else None,
    )
    db.add(postulacion)
    db.flush()
    db.add(ApplicationStatusHistory(application_id=postulacion.id, from_status=None, to_status="applied",
                                    reason="Postulación registrada", created_at=inicio))
    if estado != "applied":
        db.add(ApplicationStatusHistory(
            application_id=postulacion.id, from_status="applied", to_status=estado,
            changed_by=None if estado == "withdrawn" else reclutador.id,
            reason={"rejected": "El perfil no se ajusta a lo que busca el área.",
                    "withdrawn": "El egresado retiró su postulación."}.get(estado),
            created_at=ahora - timedelta(days=1),
        ))
    if indice is not None:
        for i in range(indice + 1):
            ultima = i == indice
            entrada = inicio + timedelta(days=i + 1)
            db.add(ApplicationStageHistory(
                application_id=postulacion.id, stage_id=etapas[i].id, entered_at=entrada,
                left_at=None if ultima and resultado == "pending" else entrada + timedelta(hours=20),
                changed_by=reclutador.id, result=resultado if ultima else "passed",
            ))
        postulacion.current_stage_id = etapas[indice].id
    db.flush()
    return postulacion, True


def _entrevista(db, postulacion: Application, horas: float, estado: str, modalidad: str,
                creador: AppUser, ahora: datetime) -> None:
    hasta = ahora + timedelta(hours=23) if horas < 24 else None
    inicio = _en_horario_laboral(ahora + timedelta(hours=horas), ahora, hasta)
    entrevista = db.scalar(select(Interview).where(Interview.application_id == postulacion.id))
    if entrevista is None:
        entrevista = Interview(application_id=postulacion.id, created_by=creador.id, modality=modalidad,
                               scheduled_start=inicio)
        db.add(entrevista)
    entrevista.scheduled_start = inicio
    entrevista.scheduled_end = inicio + timedelta(minutes=45)
    entrevista.modality = modalidad
    entrevista.status = estado
    if modalidad == "virtual":
        entrevista.meeting_url = "https://meet.google.com/egr-demo-sala"
        entrevista.location = None
        entrevista.notes = "Entrá 5 minutos antes para probar la cámara y el micrófono."
    else:
        entrevista.meeting_url = None
        entrevista.location = "Oficinas centrales, sala de reuniones 2"
        entrevista.notes = "Entrevista con el área solicitante. Traé tu CV impreso."
    db.flush()


def _conversacion(db, postulacion: Application, perfil: CandidateProfile, vacante: JobPosting,
                  miembros_empresa: list, ahora: datetime) -> bool:
    if db.scalar(select(Conversation.id).where(Conversation.application_id == postulacion.id)) is not None:
        return False
    momentos = [ahora - timedelta(days=2, hours=3), ahora - timedelta(days=1, hours=20), ahora - timedelta(hours=5)]
    conversacion = Conversation(application_id=postulacion.id, last_message_at=momentos[-1], created_at=momentos[0])
    db.add(conversacion)
    db.flush()
    # El egresado leyó hasta su respuesta: el último mensaje de la empresa le queda sin leer.
    db.add(ConversationMember(conversation_id=conversacion.id, user_id=perfil.user_id, last_read_at=momentos[1],
                              joined_at=momentos[0]))
    for user_id in miembros_empresa:
        db.add(ConversationMember(conversation_id=conversacion.id, user_id=user_id, last_read_at=momentos[-1],
                                  joined_at=momentos[0]))
    for (autor, texto), momento in zip(MENSAJES, momentos):
        db.add(Message(
            conversation_id=conversacion.id,
            sender_id=perfil.user_id if autor == "egresado" else miembros_empresa[0],
            content=texto.format(nombre=perfil.first_name.split()[0], titulo=vacante.title),
            created_at=momento,
        ))
    db.flush()
    return True


def _empresa_demo(db) -> tuple[Company, AppUser] | None:
    """La empresa de la cuenta demo empresa@prueba.com, si existe en esta base."""
    usuario = db.scalar(select(AppUser).where(AppUser.email == "empresa@prueba.com"))
    if usuario is None:
        return None
    miembro = db.scalar(select(CompanyMember).where(CompanyMember.user_id == usuario.id))
    return (db.get(Company, miembro.company_id), usuario) if miembro else None


def ejecutar() -> None:
    rng = random.Random(2026)
    ahora = datetime.now(timezone.utc)

    print("== Datos base (sembrar_multitenant) ==")
    base.ejecutar()

    print("\n== Escenario de demostración ==")
    with SessionLocal() as db:
        print("[1/6] Empresas nuevas...")
        empresas: dict[str, tuple[Company, AppUser]] = {}
        for datos in base.EMPRESAS:
            empresa = db.scalar(select(Company).where(Company.tax_id == datos["tax_id"]))
            empresas[datos["clave"]] = (empresa, db.scalar(select(AppUser).where(AppUser.email == datos["correo"])))
        for datos in EMPRESAS_NUEVAS:
            if _es_cuenta_ajena(db, datos["correo"], nit=datos["tax_id"]):
                print(f"  - Se saltea {datos['trade_name']}: {datos['correo']} ya es de otra cuenta.")
                continue
            empresa = base._empresa(db, datos)
            empresas[datos["clave"]] = (empresa, db.scalar(select(AppUser).where(AppUser.email == datos["correo"])))
        demo = _empresa_demo(db)
        if demo is not None:
            empresas["demo"] = demo
        db.commit()

        print("[2/6] Vacantes vigentes, por cerrar, recién publicadas, vencidas y en revisión...")
        vacantes = []
        orden: dict[str, int] = {}
        for clave, escenario, datos in VACANTES + (VACANTES_EMPRESA_DEMO if demo else []):
            if clave not in empresas:
                continue
            empresa, responsable = empresas[clave]
            previa = db.scalar(
                select(JobPosting).where(JobPosting.company_id == empresa.id, JobPosting.title == datos["title"])
            )
            antes = (previa.status, previa.published_at, previa.closed_at) if previa else (None, None, None)
            vacante = base._vacante(db, empresa, responsable, datos)
            _fechas(vacante, escenario, orden.setdefault(escenario, 0), ahora, antes)
            orden[escenario] += 1
            aprobadas = set(db.scalars(
                select(CompanyInstitution.institution_id).where(
                    CompanyInstitution.company_id == empresa.id, CompanyInstitution.status == "approved"
                )
            ))
            vacantes.append((vacante, escenario, responsable, aprobadas, set(datos["carreras"])))
        db.commit()

        print("[3/6] Egresados de las cuatro universidades...")
        perfiles = []
        for fila in _egresados_nuevos(rng):
            if _es_cuenta_ajena(db, fila[0], documento=fila[3]):
                print(f"  - Se saltea {fila[0]}: ya es de otra cuenta.")
                continue
            perfiles.append((fila, base._egresado(db, fila)))
        db.commit()

        print("[4/6] Postulaciones en todas las etapas...")
        antonio = db.scalar(
            select(CandidateProfile).join(AppUser, AppUser.id == CandidateProfile.user_id)
            .where(AppUser.email == "antonio@prueba.com")
        )
        nuevas = 0
        en_entrevista: list[tuple[Application, AppUser]] = []
        para_conversar = []
        for vacante, escenario, responsable, aprobadas, carreras in vacantes:
            if escenario == "revision":
                continue
            elegibles = [(fila, perfil) for fila, perfil in perfiles if fila[8] == "verified" and fila[4] in aprobadas]
            # Primero los de las carreras que pide la vacante, después el resto, como pasa en la realidad.
            elegibles.sort(key=lambda par: (par[0][6] not in carreras, rng.random()))
            estados = ESTADOS[escenario]
            elegidos = [(perfil, estados[i % len(estados)])
                        for i, (_, perfil) in enumerate(elegibles[: POSTULANTES[escenario]])]
            if vacante.title == "Analista Funcional" and antonio is not None and UAGRM in aprobadas:
                elegidos.insert(0, (antonio, "interview"))
            for perfil, estado in elegidos:
                postulacion, creada = _postular(db, perfil, vacante, estado, rng.randint(4, 14), responsable, ahora)
                nuevas += creada
                if postulacion.current_status == "interview":
                    # La cuenta demo del egresado va primero: su entrevista queda para mañana.
                    posicion = 0 if perfil is antonio else len(en_entrevista)
                    en_entrevista.insert(posicion, (postulacion, responsable))
                if postulacion.current_status in ("shortlisted", "interview", "offer") and len(para_conversar) < 10:
                    para_conversar.append((postulacion, perfil, vacante))
        db.commit()

        print("[5/6] Entrevistas de hoy, mañana y la semana que viene...")
        for i, (postulacion, responsable) in enumerate(en_entrevista):
            horas, estado, modalidad = ENTREVISTAS[i % len(ENTREVISTAS)]
            horas += 24 * 7 * (i // len(ENTREVISTAS))
            _entrevista(db, postulacion, horas, estado, modalidad, responsable, ahora)
        db.commit()

        print("[6/6] Conversaciones entre empresas y egresados...")
        conversaciones = 0
        for postulacion, perfil, vacante in para_conversar:
            miembros = list(db.scalars(
                select(CompanyMember.user_id).where(
                    CompanyMember.company_id == vacante.company_id, CompanyMember.is_active.is_(True)
                )
            ))
            if miembros:
                conversaciones += _conversacion(db, postulacion, perfil, vacante, miembros, ahora)
        db.commit()

    print(
        f"\nEscenario listo: {len(vacantes)} vacantes, {len(perfiles)} egresados, {nuevas} postulaciones nuevas, "
        f"{len(en_entrevista)} entrevistas y {conversaciones} conversaciones nuevas."
    )

    print("\n== Tareas automáticas (generan los avisos) ==")
    if "--con-tareas" in sys.argv[1:] or fcm_service.inicializar_firebase():
        for clave in ("cierre_vacantes", "boletin_ofertas", "recordatorios"):
            corrida = planificador.ejecutar(clave, disparador="manual", autor=AUTOR)
            print(f"- {clave}: {corrida.estado} · {corrida.resumen}")
    else:
        print(
            "Esta máquina no tiene Firebase. Para que los avisos lleguen también como push, entrá como "
            "superadmin a «Tareas automáticas» y tocá «Ejecutar ahora» en «Cierre de vacantes vencidas», "
            "«Boletín diario de ofertas» y «Recordatorios de cierres y entrevistas», en ese orden. "
            "Para correrlas desde acá (solo en la campana): python -m scripts.sembrar_escenario_demo --con-tareas"
        )
    print("\nListo. Las cuentas nuevas usan la contraseña de DEMO_PASSWORD.")


if __name__ == "__main__":
    ejecutar()
