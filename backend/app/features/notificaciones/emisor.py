"""Punto único para emitir notificaciones (HU-21).

Todos los módulos que avisan algo al usuario (mensajes, entrevistas, proceso de
selección) pasan por acá, así las preferencias de alertas se respetan siempre y
el aviso también sale por push cuando Firebase está configurado.
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.notificacion import Notification, NotificationPreference

logger = logging.getLogger(__name__)

# Qué preferencia controla cada tipo de notificación. Son los tipos que usan los
# módulos que notifican; los que no aparecen acá se envían siempre.
CATEGORIA_POR_TIPO: dict[str, str] = {
    **dict.fromkeys(("application_status", "stage_change"), "notify_stage_changes"),
    **dict.fromkeys(("job_match", "vacante_afinidad", "vacante_por_cerrar"), "notify_job_matches"),
    **dict.fromkeys(
        (
            "interview_proposal",
            "interview_rescheduled",
            "interview_cancelled",
            "interview_confirmed",
            "interview_rejected",
            "interview_scheduled",
            "interview_reminder",
        ),
        "notify_interview_events",
    ),
    **dict.fromkeys(("new_message", "message_received", "mensaje_nuevo"), "notify_messages"),
}


def preferencias_de(db: Session, user_id: uuid.UUID) -> NotificationPreference | None:
    """Preferencias del usuario sin crearlas; None si nunca las configuró.

    La consulta va en un savepoint: si la base todavía no tiene las columnas de la
    migración HU-21, se usan los valores por defecto en vez de abortar la
    transacción del módulo que está notificando (un mensaje, una entrevista...).
    """
    try:
        with db.begin_nested():
            return db.scalar(select(NotificationPreference).where(NotificationPreference.user_id == user_id))
    except SQLAlchemyError:
        logger.warning("No se pudieron leer las preferencias de notificación; se usan las de por defecto.")
        return None


def categoria_habilitada(pref: NotificationPreference | None, tipo: str) -> bool:
    campo = CATEGORIA_POR_TIPO.get(tipo)
    return pref is None or campo is None or bool(getattr(pref, campo))


def emitir_notificacion(
    db: Session,
    user_id: uuid.UUID,
    tipo: str,
    titulo: str,
    cuerpo: str | None = None,
    enlace: str | None = None,
) -> Notification | None:
    """Crea el aviso en la campanita y lo manda por push según las preferencias.

    No hace commit: queda en la transacción de quien llama. Devuelve None si el
    usuario no quiere avisos de este tipo dentro de la app.
    """
    pref = preferencias_de(db, user_id)
    if not categoria_habilitada(pref, tipo):
        return None

    notif = None
    if pref is None or pref.in_app_enabled:
        notif = Notification(
            user_id=user_id,
            notification_type=tipo,
            title=titulo.strip(),
            body=cuerpo.strip() if cuerpo else None,
            link=enlace.strip() if enlace else None,
        )
        db.add(notif)

    if pref is None or pref.push_enabled:
        # Import diferido: fcm_service carga firebase_admin solo si hace falta.
        from app.features.notificaciones import fcm_service

        fcm_service.enviar_push_seguro(db, user_id, titulo, cuerpo, enlace)
    return notif
