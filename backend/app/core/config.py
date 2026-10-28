from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_JWT_SECRET_POR_DEFECTO = "change-me-in-local-env-min-32-chars-please"


class Settings(BaseSettings):
    """Configuración central de la aplicación EGRESA (monolito FastAPI)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "EGRESA"
    environment: str = "local"
    api_prefix: str = "/api"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/egresa"

    jwt_secret: str = _JWT_SECRET_POR_DEFECTO
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    jwt_refresh_expire_minutes: int = 60 * 24 * 7

    cors_allowed_origins: list[str] = ["http://localhost:4200"]

    login_max_attempts: int = 5
    login_lockout_minutes: int = 15

    storage_backend: str = "local"  # local | gcs
    storage_local_path: str = "./storage"
    gcs_bucket_name: str | None = None

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "no-reply@egresa.uagrm.edu.bo"
    # Alternativa a SMTP por HTTPS (Railway bloquea SMTP en sus planes básicos).
    brevo_api_key: str | None = None

    # Contraseña de las cuentas demo de scripts.sembrar_multitenant (no se versiona).
    demo_password: str | None = None

    # Stripe Checkout: cobro anual de los planes de las universidades.
    stripe_secret_key: str | None = None
    stripe_publishable_key: str | None = None
    stripe_webhook_secret: str | None = None  # opcional: sin él se confirma al volver de Stripe
    # Adonde vuelve el navegador después de pagar (o cancelar) en Stripe.
    frontend_url: str = "http://localhost:4200"

    # Interruptor del servicio de IA (recomendaciones y afinidad). En false la plataforma
    # sigue funcionando y solo avisa que las recomendaciones no están disponibles.
    ia_recomendaciones_activas: bool = True
    # HU-28: interruptor del microservicio/asistente conversacional de orientación.
    ia_chatbot_activo: bool = True

    # Tareas automáticas diarias (copia de seguridad, cierre de vacantes vencidas, boletín
    # de ofertas). Se ejecutan una vez por día desde la hora indicada (hora de Bolivia).
    # Sin definir, corren solo en el servidor (producción o Railway), no en la computadora
    # de quien levanta el backend contra la base compartida.
    tareas_automaticas_activas: bool | None = None
    tareas_hora_diaria: int = 3
    respaldos_automaticos_conservar: int = 7

    # Bitácora confidencial: clave pública derivada de la clave de desarrollador
    # (python -m scripts.clave_bitacora). Con ella el servidor cifra cada entrada, pero
    # solo quien tiene la clave de desarrollador puede leerlas. Sin definir, la bitácora
    # se guarda sin cifrar (modo de desarrollo).
    bitacora_clave_publica: str | None = None

    @model_validator(mode="after")
    def _exigir_jwt_secret_en_produccion(self) -> "Settings":
        # El repositorio es público: con el secreto por defecto cualquiera podría firmar tokens.
        if self.environment == "production" and (
            self.jwt_secret == _JWT_SECRET_POR_DEFECTO or len(self.jwt_secret) < 32
        ):
            raise ValueError("En producción hay que definir JWT_SECRET (32 caracteres o más).")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
