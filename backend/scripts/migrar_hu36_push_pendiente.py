"""Migración aditiva e idempotente para HU-36: cola de reintento de notificaciones push.

Crea la tabla `push_pendiente` (ADR-003) con sus índices. El backend también la asegura al
arrancar mediante `app.core.esquema.asegurar_esquema_requisitos`. Solo contra BD local (ADR-002).

Uso (desde la carpeta backend):
    python -m scripts.migrar_hu36_push_pendiente
"""

from app.core.database import engine
from app.core.esquema import asegurar_esquema_requisitos


def ejecutar() -> None:
    with engine.begin() as conn:
        cambios = asegurar_esquema_requisitos(conn)
    print("Listo: " + (", ".join(cambios) if cambios else "el esquema ya incluye push_pendiente (HU-36)."))


if __name__ == "__main__":
    ejecutar()
