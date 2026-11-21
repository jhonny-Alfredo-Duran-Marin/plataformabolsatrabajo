"""Reintento de los push fallidos por un error pasajero de Firebase (HU-36 · ADR-003).

El envío original cuenta como el intento 1; se reintenta hasta 3 veces más (4 envíos en total),
solo a los dispositivos que fallaron. Los tokens que Firebase da por inválidos se desactivan en
`enviar_push_fcm` y no vuelven a la cola.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.features.notificaciones import fcm_service
from app.models.notificacion import PushPending

logger = logging.getLogger(__name__)

MAX_INTENTOS = 4  # envío original + 3 reintentos
_LOTE = 100


def reintentar_pendientes(db: Session) -> dict[str, int]:
    """Una vuelta de reintentos. Hace commit por su cuenta (sesión propia del planificador)."""
    resumen = {"revisados": 0, "enviados": 0, "pendientes": 0, "fallidos": 0}
    if not fcm_service.inicializar_firebase():
        return resumen  # sin Firebase no se gasta ningún intento

    ahora = datetime.now(timezone.utc)
    pendientes = db.scalars(
        select(PushPending)
        .where(PushPending.estado == "pendiente", PushPending.proximo_intento_at <= ahora)
        .order_by(PushPending.created_at)
        .limit(_LOTE)
        .with_for_update(skip_locked=True)
    ).all()

    for push in pendientes:
        resumen["revisados"] += 1
        try:
            with db.begin_nested():
                resultado = fcm_service.enviar_push_fcm(
                    db,
                    push.user_id,
                    push.titulo,
                    push.cuerpo,
                    push.enlace,
                    push.datos or None,
                    solo_tokens=list(push.tokens or []),
                )
        except Exception as exc:  # noqa: BLE001 - cuenta como un intento fallido más
            logger.warning("Falló el reintento del push %s", push.id, exc_info=True)
            resultado = {"tokens_pasajeros": list(push.tokens or []), "error": str(exc)[:500]}

        push.intentos += 1
        faltan = resultado.get("tokens_pasajeros") or []
        if not faltan:
            push.estado = "enviado"  # entregado, o los dispositivos que quedaban ya no están activos
            push.tokens = []
            push.ultimo_error = None
            resumen["enviados"] += 1
        else:
            push.tokens = faltan
            push.ultimo_error = resultado.get("error")
            if push.intentos >= MAX_INTENTOS:
                push.estado = "fallido"
                resumen["fallidos"] += 1
            else:
                push.proximo_intento_at = datetime.now(timezone.utc)
                resumen["pendientes"] += 1
    db.commit()
    return resumen
