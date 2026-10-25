"""Migración aditiva e idempotente para HU-28: Chatbot de orientación.

Crea o asegura las tablas `chatbot_session` y `chatbot_message` con sus índices
y restricciones de seguridad. El backend también las aplica automáticamente al
arrancar mediante `app.core.esquema.asegurar_esquema_requisitos`.

Uso (desde la carpeta backend):
    python -m scripts.migrar_hu28_chatbot
"""

from app.core.database import engine
from app.core.esquema import asegurar_esquema_requisitos


def ejecutar() -> None:
    with engine.begin() as conn:
        cambios = asegurar_esquema_requisitos(conn)
    print("Listo: " + (", ".join(cambios) if cambios else "el esquema ya incluye las tablas del chatbot (HU-28)."))


if __name__ == "__main__":
    ejecutar()
