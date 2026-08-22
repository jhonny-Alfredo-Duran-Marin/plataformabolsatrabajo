from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.common.exception_handlers import register_exception_handlers
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.routers import (
    auditoria,
    auth,
    catalogos,
    comunicacion,
    health,
    ia,
    moderacion,
    notificaciones,
    perfiles,
    postulaciones,
    reportes,
    seleccion,
    vacantes,
    validacion,
)

settings = get_settings()
configure_logging()

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
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
    auditoria.router,
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
