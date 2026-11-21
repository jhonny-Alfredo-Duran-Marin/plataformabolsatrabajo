"""Aviso al egresado cuando la empresa o el sistema cambia el estado de su postulación (HU-36).

Lo llaman los módulos que cambian `current_status` (selección, entrevistas, postulaciones) justo
después de cambiarlo. Pasa por `emitir_notificacion`, así respeta las preferencias del egresado.
El retiro que hace el propio egresado (`withdrawn`) no avisa.
"""

import logging

from sqlalchemy.orm import Session

from app.features.notificaciones.emisor import emitir_notificacion
from app.features.postulaciones.schema import ESTADOS_INFO
from app.models.notificacion import Notification
from app.models.postulacion import Application

logger = logging.getLogger(__name__)

TIPO_ESTADO_POSTULACION = "application_status"


def estado_legible(estado: str) -> str:
    return ESTADOS_INFO.get(estado, {}).get("label", estado)


def enlace_postulacion(postulacion_id: object) -> str:
    return f"/postulaciones?id={postulacion_id}"


def notificar_cambio_estado(db: Session, app: Application, detalle: str | None = None) -> Notification | None:
    """Avisa el estado actual de `app`. No hace commit: queda en la transacción de quien llama.

    Un fallo del aviso nunca revierte el cambio de estado (savepoint).
    """
    if app.current_status == "withdrawn":
        return None
    candidato = app.candidate
    vacante = app.job_posting
    if candidato is None or candidato.user_id is None or vacante is None:
        return None

    empresa = vacante.company
    nombre_empresa = (empresa.trade_name or empresa.legal_name) if empresa else None
    estado = estado_legible(app.current_status)
    cuerpo = f"Tu postulación ahora está en estado «{estado}»."
    if nombre_empresa:
        cuerpo = f"{nombre_empresa}: {cuerpo[0].lower()}{cuerpo[1:]}"
    if detalle:
        cuerpo = f"{cuerpo} {detalle}"

    try:
        with db.begin_nested():
            return emitir_notificacion(
                db,
                candidato.user_id,
                TIPO_ESTADO_POSTULACION,
                f"Tu postulación: {vacante.title}"[:200],
                cuerpo,
                enlace_postulacion(app.id),
                datos_extra={"tipo": TIPO_ESTADO_POSTULACION, "postulacion_id": str(app.id)},
            )
    except Exception:  # noqa: BLE001 - el cambio de estado y su historial se conservan
        logger.warning("No se pudo avisar el cambio de estado de la postulación %s", app.id, exc_info=True)
        return None
