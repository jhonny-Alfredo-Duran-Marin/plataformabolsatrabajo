import time

from app.common.exceptions import ForbiddenException
from app.core.config import get_settings

settings = get_settings()

_intentos_fallidos: dict[str, list[float]] = {}


def _clave(correo: str) -> str:
    # El login busca el correo sin importar mayúsculas ni espacios: el contador también, para que
    # «Admin@uni.bo» y «admin@uni.bo» no tengan cada uno sus propios intentos.
    return correo.strip().lower()


def registrar_intento_fallido(correo: str) -> None:
    ahora = time.time()
    ventana = settings.login_lockout_minutes * 60
    # De paso se descartan los contadores vencidos, para que el diccionario no crezca sin límite.
    for otro in [c for c, ts in _intentos_fallidos.items() if not ts or ahora - ts[-1] >= ventana]:
        del _intentos_fallidos[otro]
    clave = _clave(correo)
    intentos = [t for t in _intentos_fallidos.get(clave, []) if ahora - t < ventana]
    intentos.append(ahora)
    _intentos_fallidos[clave] = intentos


def limpiar_intentos(correo: str) -> None:
    _intentos_fallidos.pop(_clave(correo), None)


def verificar_bloqueo(correo: str) -> None:
    ahora = time.time()
    ventana = settings.login_lockout_minutes * 60
    intentos = [t for t in _intentos_fallidos.get(_clave(correo), []) if ahora - t < ventana]
    if len(intentos) >= settings.login_max_attempts:
        raise ForbiddenException(
            f"Cuenta bloqueada temporalmente tras {settings.login_max_attempts} intentos fallidos. "
            f"Intente nuevamente en {settings.login_lockout_minutes} minutos."
        )
