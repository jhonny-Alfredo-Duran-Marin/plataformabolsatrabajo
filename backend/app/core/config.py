from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración central de la aplicación EGRESA (monolito FastAPI)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "EGRESA"
    environment: str = "local"
    api_prefix: str = "/api"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/egresa"

    jwt_secret: str = "change-me-in-local-env-min-32-chars-please"
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
