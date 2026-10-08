"""Tareas automáticas diarias de la plataforma.

- respaldo_diario: copia de seguridad completa de la base (Backup automático, requisito 6).
- cierre_vacantes: cierra las vacantes publicadas cuya fecha límite ya pasó y avisa a la empresa.
- boletin_ofertas: avisa a cada egresado verificado las ofertas publicadas en las últimas 24 horas
  que coinciden con su perfil (motor de afinidad de HU-23), por la campana y por push.
- recordatorios: avisa lo que vence en las próximas 24 horas: vacantes por cerrar (a la empresa y a
  los egresados afines que todavía no se postularon) y entrevistas (al egresado y a la empresa).

Cada tarea recibe su propia sesión, hace commit y devuelve un resumen para el historial.
"""

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.tenancy import INSTITUCION_POR_DEFECTO_ID
from app.features.bitacora.service import BitacoraService
from app.features.ia.services import afinidad as motor_afinidad
from app.features.moderacion.reglas import no_oculta_por_denuncias
from app.features.notificaciones.emisor import emitir_notificacion
from app.features.respaldos.service import RespaldoService
from app.features.vacantes.repository import empresa_no_suspendida
from app.models.candidato import CandidateProfile
from app.models.entrevista import Interview
from app.models.empresa import CompanyMember
from app.models.institucion import CompanyInstitution
from app.models.notificacion import Notification
from app.models.postulacion import Application
from app.models.vacante import JobEducationPreference, JobPosting, JobSkill, JobStatus

_MODULO = "tareas"
# Afinidad mínima para avisar una oferta nueva en el boletín (la neutral, sin datos, es 50).
UMBRAL_BOLETIN = 60
# Qué tan adelante mira el recordatorio, y cuánto tiempo un aviso igual cuenta como ya enviado.
VENTANA_RECORDATORIO = timedelta(hours=24)
_SIN_REPETIR = timedelta(hours=20)
_ZONA_BOLIVIA = timezone(timedelta(hours=-4))
_ESTADOS_ENTREVISTA_ACTIVA = ("pending_confirmation", "confirmed", "scheduled")


@dataclass(frozen=True)
class Tarea:
    clave: str
    nombre: str
    descripcion: str
    ejecutar: Callable[[Session], str]


def _corto(texto: str, largo: int = 80) -> str:
    return texto if len(texto) <= largo else texto[: largo - 1].rstrip() + "…"


def respaldo_diario(db: Session) -> str:
    respaldo, eliminadas = RespaldoService(db).generar_automatico()
    resumen = f"Copia {respaldo.file_name}: {respaldo.tables_count} tablas y {respaldo.rows_count} filas."
    if eliminadas:
        resumen += f" Se borraron {eliminadas} copias automáticas viejas."
    return resumen


def cierre_vacantes(db: Session) -> str:
    ahora = datetime.now(timezone.utc)
    vencidas = db.scalars(
        select(JobPosting)
        .where(
            JobPosting.status == JobStatus.PUBLISHED.value,
            JobPosting.application_deadline.is_not(None),
            JobPosting.application_deadline < ahora,
        )
        .with_for_update(skip_locked=True)
    ).all()
    if not vencidas:
        return "No había vacantes vencidas."

    miembros: dict = defaultdict(list)
    filas = db.execute(
        select(CompanyMember.company_id, CompanyMember.user_id).where(
            CompanyMember.company_id.in_({v.company_id for v in vencidas}), CompanyMember.is_active.is_(True)
        )
    )
    for company_id, user_id in filas:
        miembros[company_id].append(user_id)

    for vacante in vencidas:
        vacante.status = JobStatus.CLOSED.value
        vacante.closed_at = ahora
        for user_id in miembros[vacante.company_id]:
            emitir_notificacion(
                db,
                user_id,
                "vacante_cerrada",
                f"Tu vacante cerró: {_corto(vacante.title)}",
                "Llegó a su fecha límite y dejó de recibir postulaciones. "
                "Los postulantes siguen en tu proceso de selección.",
                "/vacantes/mis-vacantes",
            )
    BitacoraService(db).registrar(
        modulo=_MODULO, accion="cerrar_vacantes_vencidas", detalles=f"cerradas={len(vencidas)}"
    )
    db.commit()
    return f"Se cerraron {len(vencidas)} vacantes vencidas y se avisó a sus empresas."


def _vacantes_vigentes(db: Session, *condiciones) -> list[JobPosting]:
    """Vacantes publicadas y visibles, con lo que necesita el motor de afinidad."""
    return list(
        db.scalars(
            select(JobPosting)
            .where(
                JobPosting.status == JobStatus.PUBLISHED.value,
                empresa_no_suspendida(),
                no_oculta_por_denuncias(),
                *condiciones,
            )
            .options(
                joinedload(JobPosting.company),
                selectinload(JobPosting.skills).joinedload(JobSkill.skill),
                selectinload(JobPosting.education_preferences).joinedload(JobEducationPreference.field_of_study),
                selectinload(JobPosting.language_requirements),
            )
        )
        .unique()
        .all()
    )


def _afines(db: Session, vacantes: list[JobPosting]) -> list[tuple[CandidateProfile, list[tuple[int, JobPosting]]]]:
    """Por egresado verificado, sus vacantes con afinidad suficiente, de mayor a menor.

    Solo cuentan las de empresas habilitadas en su universidad y a las que todavía no se postuló.
    """
    habilitadas = set(
        db.execute(
            select(CompanyInstitution.company_id, CompanyInstitution.institution_id).where(
                CompanyInstitution.company_id.in_({v.company_id for v in vacantes}),
                CompanyInstitution.status == "approved",
            )
        ).tuples()
    )
    postuladas = set(
        db.execute(
            select(Application.candidate_id, Application.job_id).where(
                Application.job_id.in_({v.id for v in vacantes})
            )
        ).tuples()
    )
    candidatos = db.scalars(select(CandidateProfile).where(CandidateProfile.verification_status == "verified")).all()
    perfiles = motor_afinidad.perfiles_de_candidatos(db, {c.id for c in candidatos})

    resultado = []
    for candidato in candidatos:
        universidad = candidato.institution_id or INSTITUCION_POR_DEFECTO_ID
        coincidencias = sorted(
            (
                (motor_afinidad.evaluar(vacante, perfiles[candidato.id]).porcentaje, vacante)
                for vacante in vacantes
                if (vacante.company_id, universidad) in habilitadas and (candidato.id, vacante.id) not in postuladas
            ),
            key=lambda par: par[0],
            reverse=True,
        )
        coincidencias = [par for par in coincidencias if par[0] >= UMBRAL_BOLETIN]
        if coincidencias:
            resultado.append((candidato, coincidencias))
    return resultado


def boletin_ofertas(db: Session) -> str:
    if not motor_afinidad.ia_activa():
        return "El servicio de IA está apagado: hoy no se envió el boletín."
    ahora = datetime.now(timezone.utc)
    nuevas = _vacantes_vigentes(
        db,
        JobPosting.published_at >= ahora - timedelta(hours=24),
        or_(JobPosting.application_deadline.is_(None), JobPosting.application_deadline >= ahora),
    )
    if not nuevas:
        return "No hubo ofertas nuevas en las últimas 24 horas."

    avisados = 0
    for candidato, coincidencias in _afines(db, nuevas):
        # Un boletín por día: si ya lo recibió (por ejemplo, la tarea se corrió a mano), no se repite.
        if _ya_avisado(db, candidato.user_id, "job_match", "/recomendaciones", ahora - _SIN_REPETIR):
            continue
        afinidad, mejor = coincidencias[0]
        empresa = mejor.company.trade_name or mejor.company.legal_name
        cuerpo = f"{_corto(mejor.title, 60)} en {empresa} ({afinidad}% de afinidad)"
        if len(coincidencias) > 1:
            cuerpo += f" y {len(coincidencias) - 1} más"
        titulo = "1 oferta nueva para vos" if len(coincidencias) == 1 else f"{len(coincidencias)} ofertas nuevas para vos"
        emitir_notificacion(db, candidato.user_id, "job_match", titulo, cuerpo + ".", "/recomendaciones")
        avisados += 1

    BitacoraService(db).registrar(
        modulo=_MODULO, accion="boletin_ofertas", detalles=f"ofertas={len(nuevas)} egresados_avisados={avisados}"
    )
    db.commit()
    return f"{len(nuevas)} ofertas nuevas en las últimas 24 horas; se avisó a {avisados} egresados."


def _ya_avisado(db: Session, user_id, tipo: str, enlace: str | None, desde: datetime) -> bool:
    """Evita repetir el mismo recordatorio si la tarea corre dos veces el mismo día."""
    consulta = select(Notification.id).where(
        Notification.user_id == user_id, Notification.notification_type == tipo, Notification.created_at >= desde
    )
    if enlace is not None:
        consulta = consulta.where(Notification.link == enlace)
    return db.scalar(consulta.limit(1)) is not None


def _cuando(momento: datetime, ahora: datetime) -> str:
    """«hoy a las 15:30» o «mañana a las 09:00», en hora de Bolivia."""
    local = momento.astimezone(_ZONA_BOLIVIA)
    hoy = ahora.astimezone(_ZONA_BOLIVIA).date()
    if local.date() == hoy:
        dia = "hoy"
    elif local.date() == hoy + timedelta(days=1):
        dia = "mañana"
    else:
        dia = f"el {local:%d/%m}"
    return f"{dia} a las {local:%H:%M}"


def _miembros_de(db: Session, empresas: set) -> dict:
    miembros: dict = defaultdict(list)
    if not empresas:
        return miembros
    filas = db.execute(
        select(CompanyMember.company_id, CompanyMember.user_id).where(
            CompanyMember.company_id.in_(empresas), CompanyMember.is_active.is_(True)
        )
    )
    for company_id, user_id in filas:
        miembros[company_id].append(user_id)
    return miembros


def _recordar_vacantes(db: Session, por_cerrar: list[JobPosting], ahora: datetime, desde: datetime) -> tuple[int, int]:
    postulaciones = dict(
        db.execute(
            select(Application.job_id, func.count(Application.id))
            .where(Application.job_id.in_({v.id for v in por_cerrar}))
            .group_by(Application.job_id)
        ).all()
    )
    miembros = _miembros_de(db, {v.company_id for v in por_cerrar})
    avisos_empresas = 0
    for vacante in por_cerrar:
        enlace = f"/vacantes/mis-vacantes?vacante={vacante.id}"
        total = postulaciones.get(vacante.id, 0)
        for user_id in miembros[vacante.company_id]:
            if _ya_avisado(db, user_id, "recordatorio_vacante", enlace, desde):
                continue
            emitir_notificacion(
                db,
                user_id,
                "recordatorio_vacante",
                f"Tu vacante cierra {_cuando(vacante.application_deadline, ahora)}: {_corto(vacante.title, 60)}",
                f"Tiene {total} {'postulación' if total == 1 else 'postulaciones'}. "
                "Si necesitás más tiempo, extendé la fecha límite.",
                enlace,
            )
            avisos_empresas += 1

    avisos_egresados = 0
    if por_cerrar and motor_afinidad.ia_activa():
        for candidato, coincidencias in _afines(db, por_cerrar):
            if _ya_avisado(db, candidato.user_id, "vacante_por_cerrar", None, desde):
                continue
            afinidad, mejor = coincidencias[0]
            empresa = mejor.company.trade_name or mejor.company.legal_name
            cuerpo = (
                f"{_corto(mejor.title, 60)} en {empresa} ({afinidad}% de afinidad) recibe postulaciones "
                f"hasta {_cuando(mejor.application_deadline, ahora)}"
            )
            if len(coincidencias) > 1:
                cuerpo += f". Cierran {len(coincidencias) - 1} más que te corresponden"
            titulo = (
                "Última oportunidad para postularte"
                if len(coincidencias) == 1
                else f"{len(coincidencias)} ofertas para vos cierran pronto"
            )
            emitir_notificacion(
                db, candidato.user_id, "vacante_por_cerrar", titulo, cuerpo + ".", f"/vacantes/{mejor.id}"
            )
            avisos_egresados += 1
    return avisos_empresas, avisos_egresados


def _recordar_entrevistas(db: Session, ahora: datetime, hasta: datetime, desde: datetime) -> tuple[int, int]:
    entrevistas = db.execute(
        select(Interview, CandidateProfile, JobPosting)
        .join(Application, Application.id == Interview.application_id)
        .join(CandidateProfile, CandidateProfile.id == Application.candidate_id)
        .join(JobPosting, JobPosting.id == Application.job_id)
        .options(joinedload(JobPosting.company))
        .where(
            Interview.status.in_(_ESTADOS_ENTREVISTA_ACTIVA),
            Interview.scheduled_start > ahora,
            Interview.scheduled_start <= hasta,
        )
    ).all()
    miembros = _miembros_de(db, {vacante.company_id for _, _, vacante in entrevistas})
    avisos = 0
    for entrevista, candidato, vacante in entrevistas:
        cuando = _cuando(entrevista.scheduled_start, ahora)
        lugar = (
            "virtual" if entrevista.modality == "virtual" else f"presencial en {entrevista.location or 'la empresa'}"
        )
        empresa = vacante.company.trade_name or vacante.company.legal_name
        pendiente = entrevista.status == "pending_confirmation"

        enlace = f"/postulaciones?entrevista={entrevista.id}"
        if not _ya_avisado(db, candidato.user_id, "interview_reminder", enlace, desde):
            emitir_notificacion(
                db,
                candidato.user_id,
                "interview_reminder",
                f"Tu entrevista es {cuando}",
                f"{_corto(vacante.title, 60)} en {empresa}, {lugar}."
                + (" Todavía no la confirmaste." if pendiente else ""),
                enlace,
            )
            avisos += 1

        nombre = f"{candidato.first_name} {candidato.last_name}".strip()
        enlace = f"/seleccion?entrevista={entrevista.id}"
        for user_id in miembros[vacante.company_id]:
            if _ya_avisado(db, user_id, "interview_reminder", enlace, desde):
                continue
            emitir_notificacion(
                db,
                user_id,
                "interview_reminder",
                f"Entrevista {cuando} con {nombre}",
                f"{_corto(vacante.title, 60)}, {lugar}." + (" Todavía no la confirmó." if pendiente else ""),
                enlace,
            )
            avisos += 1
    return len(entrevistas), avisos


def recordatorios(db: Session) -> str:
    ahora = datetime.now(timezone.utc)
    hasta = ahora + VENTANA_RECORDATORIO
    desde = ahora - _SIN_REPETIR

    por_cerrar = _vacantes_vigentes(
        db, JobPosting.application_deadline > ahora, JobPosting.application_deadline <= hasta
    )
    avisos_empresas, avisos_egresados = _recordar_vacantes(db, por_cerrar, ahora, desde)
    entrevistas, avisos_entrevistas = _recordar_entrevistas(db, ahora, hasta, desde)

    BitacoraService(db).registrar(
        modulo=_MODULO,
        accion="recordatorios",
        detalles=(
            f"vacantes={len(por_cerrar)} avisos_empresas={avisos_empresas} avisos_egresados={avisos_egresados} "
            f"entrevistas={entrevistas} avisos_entrevistas={avisos_entrevistas}"
        ),
    )
    db.commit()
    if not por_cerrar and not entrevistas:
        return "No hay vacantes ni entrevistas en las próximas 24 horas."
    return (
        f"{len(por_cerrar)} vacantes cierran en las próximas 24 horas ({avisos_empresas} avisos a empresas y "
        f"{avisos_egresados} a egresados); {entrevistas} entrevistas próximas ({avisos_entrevistas} avisos)."
    )


TAREAS: dict[str, Tarea] = {
    t.clave: t
    for t in (
        Tarea(
            "respaldo_diario",
            "Copia de seguridad automática",
            "Genera una copia completa de la base de datos y conserva las últimas copias automáticas.",
            respaldo_diario,
        ),
        Tarea(
            "cierre_vacantes",
            "Cierre de vacantes vencidas",
            "Cierra las vacantes publicadas cuya fecha límite ya pasó y avisa a la empresa.",
            cierre_vacantes,
        ),
        Tarea(
            "boletin_ofertas",
            "Boletín diario de ofertas",
            "Avisa a cada egresado verificado las ofertas nuevas del día que coinciden con su perfil.",
            boletin_ofertas,
        ),
        Tarea(
            "recordatorios",
            "Recordatorios de cierres y entrevistas",
            "Avisa las vacantes que cierran y las entrevistas que ocurren en las próximas 24 horas.",
            recordatorios,
        ),
    )
}
