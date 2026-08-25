from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.common import health
from app.common.exception_handlers import register_exception_handlers
from app.core.config import get_settings
from app.core.database import Base, engine
from app.core.logging import configure_logging
import app.models  # noqa: F401 (registra todos los modelos en el metadata)
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
from app.features.roles import router as roles
from app.features.seleccion import router as seleccion
from app.features.vacantes import router as vacantes
from app.features.validacion import router as validacion

settings = get_settings()
configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Provisional: crea las tablas faltantes al arrancar. Se reemplaza por
    # migraciones de Alembic cuando el esquema quede estable.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

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
    roles.router,
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
