from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.enums import RolNombre
from app.schemas.egresado import PerfilEgresadoResponse, PerfilEgresadoUpdateRequest, VisibilidadPerfilRequest
from app.security.dependencies import CurrentUser, require_roles
from app.services.egresado_service import EgresadoService

router = APIRouter(prefix="/perfiles", tags=["perfiles"])

_solo_egresado = require_roles(RolNombre.EGRESADO, RolNombre.ESTUDIANTE)


@router.get("/me", response_model=PerfilEgresadoResponse)
def obtener_mi_perfil(current_user: CurrentUser = Depends(_solo_egresado), db: Session = Depends(get_db)):
    return EgresadoService(db).obtener_por_usuario(current_user.id_usuario)


@router.patch("/me", response_model=PerfilEgresadoResponse)
def actualizar_mi_perfil(
    data: PerfilEgresadoUpdateRequest,
    current_user: CurrentUser = Depends(_solo_egresado),
    db: Session = Depends(get_db),
):
    return EgresadoService(db).actualizar_perfil(current_user.id_usuario, data)


@router.patch("/me/visibilidad", response_model=PerfilEgresadoResponse)
def actualizar_visibilidad(
    data: VisibilidadPerfilRequest,
    current_user: CurrentUser = Depends(_solo_egresado),
    db: Session = Depends(get_db),
):
    return EgresadoService(db).actualizar_visibilidad(current_user.id_usuario, data)
