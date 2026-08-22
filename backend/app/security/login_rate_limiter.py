import time

from app.common.exceptions import ForbiddenException
from app.core.config import get_settings

settings = get_settings()

_intentos_fallidos: dict[str, list[float]] = {}


def registrar_intento_fallido(correo: str) -> None:
    ahora = time.time()
    ventana = settings.login_lockout_minutes * 60
    intentos = [t for t in _intentos_fallidos.get(correo, []) if ahora - t < ventana]
    intentos.append(ahora)
    _intentos_fallidos[correo] = intentos


def limpiar_intentos(correo: str) -> None:
    _intentos_fallidos.pop(correo, None)


def verificar_bloqueo(correo: str) -> None:
    ahora = time.time()
    ventana = settings.login_lockout_minutes * 60
    intentos = [t for t in _intentos_fallidos.get(correo, []) if ahora - t < ventana]
    if len(intentos) >= settings.login_max_attempts:
        raise ForbiddenException(
            f"Cuenta bloqueada temporalmente tras {settings.login_max_attempts} intentos fallidos. "
            f"Intente nuevamente en {settings.login_lockout_minutes} minutos."
        )
