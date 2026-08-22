from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import get_settings

settings = get_settings()


def create_access_token(subject: str, rol: str, extra_claims: dict | None = None) -> str:
    return _create_token(subject, rol, settings.jwt_expire_minutes, "access", extra_claims)


def create_refresh_token(subject: str, rol: str) -> str:
    return _create_token(subject, rol, settings.jwt_refresh_expire_minutes, "refresh")


def _create_token(subject: str, rol: str, expire_minutes: int, token_type: str, extra_claims: dict | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "rol": rol,
        "type": token_type,
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes),
        **(extra_claims or {}),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
