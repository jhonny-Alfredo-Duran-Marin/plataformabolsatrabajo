"""Planificador de las tareas automáticas diarias.

Un hilo del propio backend revisa cada 5 minutos si a alguna tarea le toca correr: una vez
por día, desde TAREAS_HORA_DIARIA (hora de Bolivia). El historial en scheduled_task_run
evita repetir una tarea ya hecha ese día aunque el servidor se reinicie, y un candado de
PostgreSQL (pg_try_advisory_lock) evita que dos instancias del backend la corran a la vez.
"""

import logging
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.features.tareas.tareas import TAREAS
from app.models.tarea import ScheduledTaskRun

logger = logging.getLogger(__name__)

ZONA_BOLIVIA = timezone(timedelta(hours=-4))
_INTERVALO_SEGUNDOS = 300
_ESPERA_INICIAL_SEGUNDOS = 60
_CANDADO = 72_640_213  # identificador fijo del candado de PostgreSQL de las tareas
_INTENTOS_POR_DIA = 3
_SIN_RESPUESTA = timedelta(hours=2)  # una corrida "en curso" más vieja se da por muerta


@dataclass
class ResultadoCorrida:
    id: str
    tarea: str
    disparador: str
    estado: str
    resumen: str | None
    autor: str | None
    inicio: datetime
    fin: datetime | None


def planificador_activo() -> bool:
    settings = get_settings()
    if settings.tareas_automaticas_activas is not None:
        return settings.tareas_automaticas_activas
    return settings.environment == "production" or bool(os.getenv("RAILWAY_ENVIRONMENT_NAME"))


def inicio_del_dia(ahora: datetime | None = None) -> datetime:
    local = (ahora or datetime.now(timezone.utc)).astimezone(ZONA_BOLIVIA)
    return local.replace(hour=0, minute=0, second=0, microsecond=0)


def proxima_ejecucion(ultima_exitosa_hoy: bool, ahora: datetime | None = None) -> datetime:
    """Cuándo vuelve a correr la tarea de forma automática."""
    ahora = ahora or datetime.now(timezone.utc)
    hoy = inicio_del_dia(ahora) + timedelta(hours=get_settings().tareas_hora_diaria)
    if ultima_exitosa_hoy or ahora.astimezone(ZONA_BOLIVIA) >= hoy + timedelta(days=1):
        return hoy + timedelta(days=1)
    return max(hoy, ahora.astimezone(ZONA_BOLIVIA))


def le_toca(db: Session, clave: str, ahora: datetime | None = None) -> bool:
    ahora = ahora or datetime.now(timezone.utc)
    inicio = inicio_del_dia(ahora)
    if ahora.astimezone(ZONA_BOLIVIA) < inicio + timedelta(hours=get_settings().tareas_hora_diaria):
        return False
    corridas = db.scalars(
        select(ScheduledTaskRun).where(
            ScheduledTaskRun.task == clave,
            ScheduledTaskRun.trigger == "automatico",
            ScheduledTaskRun.started_at >= inicio,
        )
    ).all()
    if any(c.status == "success" for c in corridas):
        return False
    if any(c.status == "running" and ahora - c.started_at < _SIN_RESPUESTA for c in corridas):
        return False
    # Una corrida que quedó «running» más allá del plazo (el proceso se cayó a mitad) cuenta como fallida,
    # para que los reintentos del día sigan teniendo tope.
    fallidas = sum(c.status == "failure" or c.status == "running" for c in corridas)
    return fallidas < _INTENTOS_POR_DIA


def resultado_de(corrida: ScheduledTaskRun) -> ResultadoCorrida:
    return ResultadoCorrida(
        id=str(corrida.id),
        tarea=corrida.task,
        disparador=corrida.trigger,
        estado=corrida.status,
        resumen=corrida.summary,
        autor=corrida.triggered_by_email,
        inicio=corrida.started_at,
        fin=corrida.finished_at,
    )


def ejecutar(clave: str, disparador: str = "automatico", autor: str | None = None) -> ResultadoCorrida:
    """Corre una tarea y deja constancia en el historial; un error no corta al planificador."""
    tarea = TAREAS[clave]
    with SessionLocal() as db:
        corrida = ScheduledTaskRun(task=clave, trigger=disparador, status="running", triggered_by_email=autor)
        db.add(corrida)
        db.commit()
        corrida_id = corrida.id

    with SessionLocal() as db:
        try:
            resumen, estado = tarea.ejecutar(db), "success"
        except Exception as exc:  # noqa: BLE001 - se registra y se reintenta en la próxima vuelta
            db.rollback()
            logger.exception("Falló la tarea automática %s", clave)
            resumen, estado = f"Error: {exc}", "failure"

    with SessionLocal() as db:
        corrida = db.get(ScheduledTaskRun, corrida_id)
        corrida.status = estado
        corrida.summary = resumen[:500]
        corrida.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(corrida)
        return resultado_de(corrida)


def revisar() -> list[ResultadoCorrida]:
    """Una vuelta del planificador: corre las tareas a las que les toca."""
    corridas: list[ResultadoCorrida] = []
    # En autocommit: el candado es de la sesión y la conexión no queda «idle in transaction»
    # mientras corren tareas largas como la copia de seguridad.
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        if not conn.execute(text("SELECT pg_try_advisory_lock(:c)"), {"c": _CANDADO}).scalar():
            return corridas  # otra instancia ya está corriendo las tareas
        try:
            for clave in TAREAS:
                # Si falla la consulta o el registro de una tarea, las siguientes corren igual.
                try:
                    with SessionLocal() as db:
                        toca = le_toca(db, clave)
                    if toca:
                        corridas.append(ejecutar(clave))
                except Exception:  # noqa: BLE001 - se reintenta en la próxima vuelta
                    logger.exception("No se pudo revisar o registrar la tarea automática %s", clave)
        finally:
            try:
                conn.execute(text("SELECT pg_advisory_unlock(:c)"), {"c": _CANDADO})
            except Exception:  # noqa: BLE001 - al cerrarse la conexión el candado se libera solo
                logger.warning("No se pudo liberar el candado de tareas; se libera al cerrar la conexión.")
    return corridas


class Planificador:
    def __init__(self) -> None:
        self._detener = threading.Event()
        self._hilo: threading.Thread | None = None

    def iniciar(self) -> None:
        if not planificador_activo():
            logger.info("Tareas automáticas desactivadas en este entorno.")
            return
        self._hilo = threading.Thread(target=self._bucle, name="tareas-diarias", daemon=True)
        self._hilo.start()
        logger.info("Tareas automáticas activas: corren cada día desde las %02d:00.", get_settings().tareas_hora_diaria)

    def detener(self) -> None:
        self._detener.set()

    def _bucle(self) -> None:
        if self._detener.wait(_ESPERA_INICIAL_SEGUNDOS):
            return
        while True:
            try:
                for corrida in revisar():
                    logger.info("Tarea %s: %s (%s)", corrida.tarea, corrida.estado, corrida.resumen)
            except Exception:  # noqa: BLE001 - p. ej. la base no responde: se reintenta en 5 minutos
                logger.exception("Falló la revisión de tareas automáticas")
            if self._detener.wait(_INTERVALO_SEGUNDOS):
                return


planificador = Planificador()
