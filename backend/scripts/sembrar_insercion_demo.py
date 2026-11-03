"""Datos de demostración de inserción laboral (HU-29 a HU-32) sobre el escenario de demostración.

Para que el registro de colocaciones, las encuestas laborales, el tablero de indicadores y su
exportación muestren números, agrega en cada una de las cuatro universidades cliente:

- 12 egresados de promociones anteriores (2022 a 2025), validados; 9 de ellos ya trabajan;
- la colocación confirmada de esos 9, registrada a mano por la universidad, con fechas de inicio
  repartidas entre 2023 y 2026;
- 3 contrataciones hechas por la plataforma a egresados del escenario: 2 colocaciones confirmadas
  y 1 sugerida que espera la confirmación del admin (con su aviso en la campana);
- la encuesta de situación laboral del período 2026-1 (ya cerrada) y la del 2026-2 (abierta),
  respondidas por parte de los egresados según su situación en ese momento.

Las cuentas de prueba del README (antonio@prueba.com, egresado.prueba@uagrm.bo y los egresados de
sembrar_multitenant) no responden: así se puede mostrar en vivo cómo se responde la encuesta.

No manda avisos de encuesta ni push y no cambia datos que no sembró. Es idempotente: busca por
correo, por egresado (una colocación cada uno), por universidad y período (encuestas) y por
egresado y encuesta (respuestas), así que volver a correrlo no duplica nada. Las cuentas nuevas
usan la contraseña DEMO_PASSWORD de backend/.env.

Requiere el escenario de demostración (python -m scripts.sembrar_escenario_demo).

Uso (desde la carpeta backend):
    python -m scripts.sembrar_insercion_demo
"""

import random
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select

import app.models  # noqa: F401 - registra todos los modelos
from app.core.database import SessionLocal
from app.features.colocaciones.repository import ColocacionRepository
from app.features.colocaciones.service import TIPO_AVISO as AVISO_COLOCACION
from app.features.encuestas.service import _PREGUNTAS
from app.features.notificaciones.emisor import emitir_notificacion
from app.models.candidato import CandidateEducation, CandidateProfile
from app.models.colocacion import Placement
from app.models.empresa import Company
from app.models.encuesta import Survey, SurveyAnswer, SurveyQuestion, SurveyQuestionOption, SurveyResponse
from app.models.institucion import CompanyInstitution
from app.models.postulacion import ApplicationStatusHistory
from app.models.usuario import AppUser
from app.models.vacante import JobPosting
from scripts import sembrar_escenario_demo as escenario
from scripts import sembrar_multitenant as base
from scripts.sembrar_multitenant import UAGRM, UMSA, UMSS, UNIFRANZ

ZONA_BOLIVIA = escenario.ZONA_BOLIVIA
UNIVERSIDADES = (UAGRM, UMSS, UMSA, UNIFRANZ)
ADMINS = {
    UAGRM: "admin@uagrm.bo",
    UMSS: "admin@umss.egresa.bo",
    UMSA: "admin@umsa.egresa.bo",
    UNIFRANZ: "admin@unifranz.egresa.bo",
}
PREFIJO_CI = {UAGRM: "7714", UMSS: "5514", UMSA: "4414", UNIFRANZ: "8814"}
# Cuentas que se dejan sin responder para mostrar la encuesta en vivo.
RESERVADAS = {"antonio@prueba.com", "egresado.prueba@uagrm.bo"} | {fila[0] for fila in base.EGRESADOS}

NOMBRES = [
    "Agustín", "Belén", "Rafael", "Tatiana", "Hugo", "Lorena", "Ernesto", "Pamela", "Joaquín", "Noelia", "Martín",
    "Viviana", "Esteban", "Carolina", "Franco", "Liliana", "Gustavo", "Rebeca", "Leonardo", "Mónica", "Raúl",
    "Susana", "Patricio", "Gisela", "Rubén", "Karina", "Sebastián", "Elena", "Tomás", "Ingrid", "Mateo", "Fernanda",
    "Nicolás", "Lourdes", "Emilio", "Rosa", "Alberto", "Yesenia", "Julio", "Teresa", "Ramiro", "Beatriz", "Pablo",
    "Lizeth", "Germán", "Milenka", "Edwin", "Nayeli",
]
APELLIDOS = [
    "Arteaga", "Bustillos", "Cabrera", "Dorado", "Escobar", "Frías", "Gamarra", "Herrera", "Iriarte", "Jordán",
    "Lara", "Maldonado", "Navarro", "Ortiz", "Prado", "Quiroz", "Roca", "Sandoval", "Tejerina", "Urquieta",
    "Velasco", "Zurita", "Aliaga", "Barrientos", "Coca", "Durán", "Eguez", "Fuentes", "Galarza", "Hurtado", "Ibáñez",
    "Jiménez", "Lozada", "Nogales", "Oropeza", "Parada", "Quintana", "Rivas", "Salinas", "Torrico", "Ugarte",
    "Zabala", "Ayala", "Castedo", "Daza", "Espinoza", "Gemio", "Heredia",
]
# Carrera de cada egresado de promociones anteriores, en el orden en que se siembran.
CARRERAS = {
    UAGRM: ["sistemas", "sistemas", "informatica", "industrial", "sistemas", "contaduria", "administracion",
            "sistemas", "economia", "informatica", "redes", "industrial"],
    UMSS: ["sistemas", "economia", "informatica", "industrial", "sistemas", "administracion", "contaduria",
           "informatica", "sistemas", "economia", "redes", "industrial"],
    UMSA: ["economia", "contaduria", "sistemas", "economia", "administracion", "sistemas", "contaduria",
           "economia", "redes", "sistemas", "administracion", "industrial"],
    UNIFRANZ: ["administracion", "sistemas", "informatica", "administracion", "contaduria", "sistemas",
               "economia", "informatica", "administracion", "sistemas", "redes", "industrial"],
}
ANIOS_EGRESO = [2022, 2023, 2023, 2024, 2024, 2024, 2024, 2025, 2025, 2025, 2025, 2025]
TRABAJAN = 9  # los primeros de cada universidad ya consiguieron empleo; los demás lo buscan
# Cargos y empleadores posibles por carrera: claves de empresas sembradas o nombres libres.
EMPLEOS = {
    "sistemas": (["Desarrollador Backend", "Analista Programador", "Ingeniero de Software Junior",
                  "Desarrollador Full Stack"], ["andes", "altiplano", "pampa", "Consultora Mburucuyá S.R.L."]),
    "informatica": (["Desarrollador Frontend", "Desarrollador Mobile", "Desarrollador Web"],
                    ["andes", "pampa", "Estudio Digital Tajibo"]),
    "industrial": (["Analista de Procesos", "Supervisor de Producción", "Analista de Logística"],
                   ["oriente", "chiquitano", "mercado"]),
    "administracion": (["Asistente Administrativo", "Analista de Recursos Humanos", "Ejecutivo Comercial"],
                       ["mercado", "horizonte", "Distribuidora El Trébol Azul"]),
    "contaduria": (["Asistente Contable", "Auditor Junior", "Analista Tributario"],
                   ["vallefin", "horizonte", "Estudio Contable Paitití"]),
    "economia": (["Analista Económico", "Analista de Créditos", "Analista de Riesgos"],
                 ["vallefin", "horizonte", "altiplano"]),
    "redes": (["Técnico de Redes", "Administrador de Infraestructura", "Soporte de Sistemas"],
              ["pampa", "Telecom Sur Andino", "andes"]),
}
SALARIOS = [None, 4500, 5200, 6000, 6800, 7500, 8200]
OTRAS_SITUACIONES = (["buscando", "posgrado", "independiente", "sin_buscar"], [5, 2, 2, 1])
TRABAJO_PROPIO = ["Consultoría independiente", "Servicios profesionales por cuenta propia", "Tienda en línea propia"]
DESCRIPCION_ENCUESTA = (
    "Contanos cómo estás laboralmente: con tus respuestas la universidad mide la inserción laboral de sus "
    "egresados y mejora la formación. Solo se publican totales."
)


def _momento(dia: date, hora: int, minuto: int = 0) -> datetime:
    return datetime.combine(dia, time(hora, minuto), tzinfo=ZONA_BOLIVIA).astimezone(timezone.utc)


def _promociones(hoy: date) -> list[dict]:
    """Egresados de promociones anteriores y, para los que trabajan, su empleo."""
    rng = random.Random(20261103)
    egresados = []
    for indice, nombre in enumerate(NOMBRES):
        universidad = UNIVERSIDADES[indice // 12]
        posicion = indice % 12
        apellido = APELLIDOS[indice]
        carrera = CARRERAS[universidad][posicion]
        area, habilidades = escenario.PERFIL_CARRERA[carrera]
        anio = ANIOS_EGRESO[posicion]
        cargos, empleadores = EMPLEOS[carrera]
        cargo, empleador = rng.choice(cargos), rng.choice(empleadores)
        inicio = date(anio, 12, 31) + timedelta(days=rng.randint(60, 300))
        if inicio > hoy - timedelta(days=10):
            inicio = hoy - timedelta(days=10 + 3 * posicion)
        egresados.append({
            "fila": (
                f"{escenario._slug(nombre)}.{escenario._slug(apellido)}@{escenario.DOMINIO[universidad]}",
                nombre, f"{apellido} {APELLIDOS[(indice * 5 + 7) % len(APELLIDOS)]}",
                f"{PREFIJO_CI[universidad]}{posicion:03d}", universidad,
                escenario.CIUDADES[universidad][posicion % len(escenario.CIUDADES[universidad])], carrera, anio,
                "verified", cargo if posicion < TRABAJAN else area, rng.sample(habilidades, k=4),
            ),
            "trabaja": posicion < TRABAJAN,
            "cargo": cargo,
            "empleador": empleador,
            "inicio": inicio,
            "salario": rng.choice(SALARIOS),
        })
    return egresados


def _empresas(db) -> dict[str, tuple[Company, AppUser | None]]:
    """Empresas sembradas por su clave, con su responsable."""
    datos = {d["tax_id"]: d for d in base.EMPRESAS + escenario.EMPRESAS_NUEVAS}
    empresas = {}
    for empresa in db.scalars(select(Company).where(Company.tax_id.in_(datos))):
        d = datos[empresa.tax_id]
        empresas[d["clave"]] = (empresa, db.scalar(select(AppUser).where(AppUser.email == d["correo"])))
    return empresas


def _tiene_colocacion(db, perfil: CandidateProfile) -> bool:
    return db.scalar(select(Placement.id).where(Placement.candidate_id == perfil.id).limit(1)) is not None


def _colocaciones_manuales(db, universidad, empresas, admin, hoy) -> int:
    nuevas = 0
    for egresado in _promociones(hoy):
        fila = egresado["fila"]
        if fila[4] != universidad:
            continue
        if escenario._es_cuenta_ajena(db, fila[0], documento=fila[3]):
            print(f"  - Se saltea {fila[0]}: ya es de otra cuenta.")
            continue
        perfil = base._egresado(db, fila)
        perfil.job_search_status = "open_to_offers" if egresado["trabaja"] else "actively_looking"
        if not egresado["trabaja"] or _tiene_colocacion(db, perfil):
            continue
        empresa = empresas.get(egresado["empleador"])
        db.add(Placement(
            candidate_id=perfil.id,
            institution_id=universidad,
            company_id=empresa[0].id if empresa else None,
            company_name=None if empresa else egresado["empleador"],
            position_title=egresado["cargo"],
            start_date=egresado["inicio"],
            salary=Decimal(egresado["salario"]) if egresado["salario"] else None,
            currency="BOB" if egresado["salario"] else None,
            status="confirmed",
            source="manual",
            created_by=admin.id if admin else None,
            created_at=_momento(egresado["inicio"] + timedelta(days=20), 10),
        ))
        nuevas += 1
    db.flush()
    return nuevas


def _contrataciones_plataforma(db, universidad, empresas, ahora, hoy) -> tuple[int, int]:
    """Tres egresados del escenario contratados por la plataforma: dos confirmadas y una por confirmar."""
    filas = [f for f in escenario._egresados_nuevos(random.Random(2026)) if f[4] == universidad and f[8] == "verified"]
    # Primero los de Sistemas: así el filtro por carrera del tablero también tiene datos.
    filas.sort(key=lambda f: (f[6] != "sistemas", f[0]))
    perfiles = []
    for fila in filas:
        perfil = db.scalar(
            select(CandidateProfile).join(AppUser, AppUser.id == CandidateProfile.user_id).where(AppUser.email == fila[0])
        )
        if perfil is not None and perfil.document_number == fila[3]:
            perfiles.append((fila, perfil))

    por_plataforma = list(db.scalars(
        select(Placement).where(Placement.source == "platform",
                                Placement.candidate_id.in_([p.id for _, p in perfiles]))
    ))
    confirmadas = sum(c.status == "confirmed" for c in por_plataforma)
    sugeridas = sum(c.status == "suggested" for c in por_plataforma)
    aprobadas = set(db.scalars(
        select(CompanyInstitution.company_id).where(
            CompanyInstitution.institution_id == universidad, CompanyInstitution.status == "approved"
        )
    ))
    rng = random.Random(f"plataforma-{universidad}")
    creadas = [0, 0]
    for fila, perfil in perfiles:
        if confirmadas + sugeridas >= 3:
            break
        if _tiene_colocacion(db, perfil):
            continue
        # La vacante: de una empresa habilitada en la universidad y, si se puede, de su carrera.
        opciones = [
            (clave, esc, datos) for clave, esc, datos in escenario.VACANTES
            if esc in ("vencida", "vigente") and clave in empresas and empresas[clave][0].id in aprobadas
        ]
        opciones.sort(key=lambda o: (fila[6] not in o[2]["carreras"], o[1] != "vencida", o[2]["title"]))
        for clave, _, datos in opciones:
            empresa, responsable = empresas[clave]
            vacante = db.scalar(
                select(JobPosting).where(JobPosting.company_id == empresa.id, JobPosting.title == datos["title"])
            )
            if vacante is None or responsable is None:
                continue
            postulacion, creada = escenario._postular(
                db, perfil, vacante, "hired", rng.randint(35, 50), responsable, ahora
            )
            if not creada:
                continue
            contratado = db.scalar(select(ApplicationStatusHistory).where(
                ApplicationStatusHistory.application_id == postulacion.id,
                ApplicationStatusHistory.to_status == "hired",
            ))
            colocacion = Placement(
                application_id=postulacion.id,
                candidate_id=perfil.id,
                institution_id=universidad,
                company_id=empresa.id,
                position_title=vacante.title[:200],
                source="platform",
                created_by=responsable.id,
            )
            if confirmadas < 2:
                # Contratado hace unas semanas y confirmado por la universidad con la fecha real.
                contratado.created_at = postulacion.applied_at + timedelta(days=12)
                colocacion.status = "confirmed"
                colocacion.start_date = (contratado.created_at + timedelta(days=7)).astimezone(ZONA_BOLIVIA).date()
                colocacion.created_at = contratado.created_at
                confirmadas += 1
                creadas[0] += 1
            else:
                # Igual que cuando la empresa lo pasa a «Contratado» (HU-29, CP02): queda por confirmar.
                colocacion.status = "suggested"
                colocacion.start_date = hoy
                sugeridas += 1
                creadas[1] += 1
                nombre = f"{perfil.first_name} {perfil.last_name}".strip()
                for admin_id in ColocacionRepository(db).admins_de_institucion(universidad):
                    emitir_notificacion(
                        db, admin_id, AVISO_COLOCACION, "Colocación por confirmar",
                        f"{nombre} figura como contratado/a para «{colocacion.position_title}». "
                        "Revisá y confirmá la colocación.",
                        "/admin/colocaciones",
                    )
            db.add(colocacion)
            db.flush()
            break
    return creadas[0], creadas[1]


def _encuesta(db, universidad, periodo: str, enviada: datetime, vence: datetime, admin) -> tuple[Survey, bool]:
    encuesta = db.scalar(select(Survey).where(
        Survey.institution_id == universidad,
        Survey.field_of_study_id.is_(None),
        func.lower(Survey.period) == periodo.lower(),
    ))
    if encuesta is not None:
        return encuesta, False
    encuesta = Survey(
        title=f"Situación laboral de egresados {periodo}",
        description=DESCRIPCION_ENCUESTA,
        period=periodo,
        target_scope="institution",
        institution_id=universidad,
        created_by=admin.id if admin else None,
        is_active=True,
        starts_at=enviada,
        expires_at=vence,
        created_at=enviada,
    )
    # Las mismas preguntas fijas que arma EncuestaService.crear (con sus códigos estables).
    for posicion, (codigo, texto, tipo, obligatoria, opciones) in enumerate(_PREGUNTAS, start=1):
        pregunta = SurveyQuestion(code=codigo, question_text=texto, question_type=tipo, is_required=obligatoria,
                                  position=posicion)
        pregunta.options = [
            SurveyQuestionOption(code=cod, option_text=etiqueta, position=n)
            for n, (cod, etiqueta) in enumerate(opciones, start=1)
        ]
        encuesta.questions.append(pregunta)
    db.add(encuesta)
    db.flush()
    return encuesta, True


def _primer_empleo(db, universidad) -> dict:
    """Primer empleo registrado de cada egresado: (inicio, empresa, cargo)."""
    empleos = {}
    for c in db.scalars(
        select(Placement)
        .where(Placement.institution_id == universidad, Placement.deleted_at.is_(None),
               Placement.status.in_(("confirmed", "suggested")))
        .order_by(Placement.start_date)
    ):
        if c.candidate_id not in empleos:
            empresa = (c.company.trade_name or c.company.legal_name) if c.company else c.company_name
            empleos[c.candidate_id] = (c.start_date, empresa, c.position_title)
    return empleos


def _responder(db, encuesta: Survey, universidad, tasa: float, desde: datetime, hasta: datetime) -> int:
    egresados = db.execute(
        select(CandidateProfile, AppUser.email)
        .join(AppUser, AppUser.id == CandidateProfile.user_id)
        .where(CandidateProfile.institution_id == universidad, CandidateProfile.verification_status == "verified",
               AppUser.account_status == "active")
        .order_by(AppUser.email)
    ).all()
    ya = set(db.scalars(select(SurveyResponse.candidate_id).where(SurveyResponse.survey_id == encuesta.id)))
    egresos = dict(db.execute(
        select(CandidateEducation.candidate_id, func.max(CandidateEducation.graduation_date))
        .where(CandidateEducation.candidate_id.in_([p.id for p, _ in egresados]),
               CandidateEducation.graduation_date.is_not(None))
        .group_by(CandidateEducation.candidate_id)
    ).all())
    empleos = _primer_empleo(db, universidad)
    preguntas = {p.code: p for p in encuesta.questions}
    situaciones = {o.code: o.id for o in preguntas["situacion_laboral"].options}
    rng = random.Random(f"{universidad}-{encuesta.period}")
    nuevas = 0
    for perfil, correo in egresados:
        # El sorteo va primero para que volver a correrlo elija a los mismos egresados.
        if rng.random() >= tasa or correo in RESERVADAS or perfil.id in ya:
            continue
        r = random.Random(f"{encuesta.period}-{perfil.id}")
        momento = desde + (hasta - desde) * r.random()
        egreso = egresos.get(perfil.id)
        empleo = empleos.get(perfil.id)
        trabajo = None
        if empleo and empleo[0] <= momento.astimezone(ZONA_BOLIVIA).date():
            situacion = "empleado"
            meses = round((empleo[0] - egreso).days / 30.4375) if egreso and empleo[0] > egreso else r.randint(2, 8)
            trabajo = (empleo[1], empleo[2], r.choice([3, 4, 4, 5, 5]), meses)
        else:
            situacion = r.choices(*OTRAS_SITUACIONES)[0]
            if situacion == "independiente":
                trabajo = ("Emprendimiento propio", r.choice(TRABAJO_PROPIO), r.choice([2, 3, 4]), r.randint(3, 12))
        respuestas = [SurveyAnswer(question_id=preguntas["situacion_laboral"].id,
                                   selected_option_id=situaciones[situacion], created_at=momento)]
        if trabajo:
            empresa, cargo, relacion, meses = trabajo
            respuestas += [
                SurveyAnswer(question_id=preguntas["empresa"].id, answer_text=empresa, created_at=momento),
                SurveyAnswer(question_id=preguntas["cargo"].id, answer_text=cargo, created_at=momento),
                SurveyAnswer(question_id=preguntas["relacion_carrera"].id, answer_number=Decimal(relacion),
                             created_at=momento),
                SurveyAnswer(question_id=preguntas["meses_primer_empleo"].id, answer_number=Decimal(meses),
                             created_at=momento),
            ]
        db.add(SurveyResponse(survey_id=encuesta.id, candidate_id=perfil.id, submitted_at=momento,
                              answers=respuestas))
        nuevas += 1
    db.flush()
    return nuevas


def ejecutar() -> None:
    ahora = datetime.now(timezone.utc)
    hoy = ahora.astimezone(ZONA_BOLIVIA).date()
    with SessionLocal() as db:
        if db.scalar(select(AppUser.id).where(AppUser.email == "maria.rojas@uagrm.egresa.bo")) is None:
            print("Falta el escenario de demostración: corré antes python -m scripts.sembrar_escenario_demo")
            return
        empresas = _empresas(db)
        for universidad in UNIVERSIDADES:
            admin = db.scalar(select(AppUser).where(AppUser.email == ADMINS[universidad]))
            print(f"== {escenario.DOMINIO[universidad].split('.')[0].upper()} ==")

            manuales = _colocaciones_manuales(db, universidad, empresas, admin, hoy)
            confirmadas, sugeridas = _contrataciones_plataforma(db, universidad, empresas, ahora, hoy)
            db.commit()
            print(f"  Colocaciones nuevas: {manuales} registradas a mano, {confirmadas} confirmadas y "
                  f"{sugeridas} por confirmar de la plataforma.")

            primera, creada1 = _encuesta(db, universidad, "2026-1", _momento(date(2026, 6, 1), 9),
                                         _momento(date(2026, 6, 30), 23, 59), admin)
            respuestas1 = _responder(db, primera, universidad, 0.8, _momento(date(2026, 6, 2), 10),
                                     _momento(date(2026, 6, 28), 19))
            enviada = _momento(hoy - timedelta(days=9), 9)
            segunda, creada2 = _encuesta(db, universidad, "2026-2", enviada, _momento(date(2026, 11, 30), 23, 59),
                                         admin)
            respuestas2 = _responder(db, segunda, universidad, 0.6, (segunda.starts_at or enviada) + timedelta(hours=2),
                                     ahora - timedelta(hours=1))
            db.commit()
            print(f"  Encuesta 2026-1 ({'nueva' if creada1 else 'ya estaba'}): {respuestas1} respuestas nuevas. "
                  f"Encuesta 2026-2 ({'nueva' if creada2 else 'ya estaba'}): {respuestas2} respuestas nuevas.")

    print("\nListo. Las cuentas nuevas usan la contraseña de DEMO_PASSWORD.")


if __name__ == "__main__":
    ejecutar()
