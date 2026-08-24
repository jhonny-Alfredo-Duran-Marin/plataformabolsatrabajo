from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.common import health
from app.common.exception_handlers import register_exception_handlers
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.features.auth import router as auth
from app.features.bitacora import router as bitacora
from app.features.catalogo import router as catalogos
from app.features.comunicacion import router as comunicacion
from app.features.ia import router as ia
from app.features.moderacion import router as moderacion
from app.features.notificaciones import router as notificaciones
from app.features.perfil import router as perfiles
from app.features.postulaciones import router as postulaciones
from app.features.reportes import router as reportes
from app.features.seleccion import router as seleccion
from app.features.vacantes import router as vacantes
from app.features.validacion import router as validacion

settings = get_settings()
configure_logging()

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200", "http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

routers = [
    health.router,
    auth.router,
    perfiles.router,
    validacion.router,
    bitacora.router,
    catalogos.router,
    vacantes.router,
    postulaciones.router,
    seleccion.router,
    comunicacion.router,
    notificaciones.router,
    moderacion.router,
    reportes.router,
    ia.router,
]

for router in routers:
    app.include_router(router, prefix=settings.api_prefix)
