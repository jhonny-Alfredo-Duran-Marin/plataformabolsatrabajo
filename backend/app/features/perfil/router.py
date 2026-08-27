from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.features.perfil.schema import (
    CertificacionRequest,
    CertificacionResponse,
    ExperienciaRequest,
    ExperienciaResponse,
    FormacionRequest,
    FormacionResponse,
    HabilidadResponse,
    HabilidadesRequest,
    IdiomaRequest,
    IdiomaResponse,
    PerfilEgresadoResponse,
    PerfilEgresadoUpdateRequest,
    VisibilidadPerfilRequest,
)
from app.security.dependencies import CurrentUser, require_roles
from app.features.perfil.service import EgresadoService

router = APIRouter(prefix="/perfiles", tags=["perfiles"])

_solo_egresado = require_roles("candidate")


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


@router.get("/me/cv")
def descargar_cv(current_user: CurrentUser = Depends(_solo_egresado), db: Session = Depends(get_db)):
    contenido, nombre_archivo = EgresadoService(db).generar_cv_pdf(current_user.id_usuario)
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={nombre_archivo}"},
    )


@router.get("/me/formacion", response_model=list[FormacionResponse])
def listar_formacion(current_user: CurrentUser = Depends(_solo_egresado), db: Session = Depends(get_db)):
    return EgresadoService(db).listar_formacion(current_user.id_usuario)


@router.post("/me/formacion", response_model=FormacionResponse, status_code=201)
def crear_formacion(
    data: FormacionRequest, current_user: CurrentUser = Depends(_solo_egresado), db: Session = Depends(get_db)
):
    return EgresadoService(db).crear_formacion(current_user.id_usuario, data)


@router.delete("/me/formacion/{item_id}", status_code=204)
def eliminar_formacion(
    item_id: str, current_user: CurrentUser = Depends(_solo_egresado), db: Session = Depends(get_db)
):
    EgresadoService(db).eliminar_formacion(current_user.id_usuario, item_id)


@router.get("/me/experiencia", response_model=list[ExperienciaResponse])
def listar_experiencia(current_user: CurrentUser = Depends(_solo_egresado), db: Session = Depends(get_db)):
    return EgresadoService(db).listar_experiencia(current_user.id_usuario)


@router.post("/me/experiencia", response_model=ExperienciaResponse, status_code=201)
def crear_experiencia(
    data: ExperienciaRequest, current_user: CurrentUser = Depends(_solo_egresado), db: Session = Depends(get_db)
):
    return EgresadoService(db).crear_experiencia(current_user.id_usuario, data)


@router.delete("/me/experiencia/{item_id}", status_code=204)
def eliminar_experiencia(
    item_id: str, current_user: CurrentUser = Depends(_solo_egresado), db: Session = Depends(get_db)
):
    EgresadoService(db).eliminar_experiencia(current_user.id_usuario, item_id)


@router.get("/me/idiomas", response_model=list[IdiomaResponse])
def listar_idiomas(current_user: CurrentUser = Depends(_solo_egresado), db: Session = Depends(get_db)):
    return EgresadoService(db).listar_idiomas(current_user.id_usuario)


@router.post("/me/idiomas", response_model=IdiomaResponse, status_code=201)
def crear_idioma(
    data: IdiomaRequest, current_user: CurrentUser = Depends(_solo_egresado), db: Session = Depends(get_db)
):
    return EgresadoService(db).crear_idioma(current_user.id_usuario, data)


@router.delete("/me/idiomas/{item_id}", status_code=204)
def eliminar_idioma(item_id: str, current_user: CurrentUser = Depends(_solo_egresado), db: Session = Depends(get_db)):
    EgresadoService(db).eliminar_idioma(current_user.id_usuario, item_id)


@router.get("/me/certificaciones", response_model=list[CertificacionResponse])
def listar_certificaciones(current_user: CurrentUser = Depends(_solo_egresado), db: Session = Depends(get_db)):
    return EgresadoService(db).listar_certificaciones(current_user.id_usuario)


@router.post("/me/certificaciones", response_model=CertificacionResponse, status_code=201)
def crear_certificacion(
    data: CertificacionRequest, current_user: CurrentUser = Depends(_solo_egresado), db: Session = Depends(get_db)
):
    return EgresadoService(db).crear_certificacion(current_user.id_usuario, data)


@router.delete("/me/certificaciones/{item_id}", status_code=204)
def eliminar_certificacion(
    item_id: str, current_user: CurrentUser = Depends(_solo_egresado), db: Session = Depends(get_db)
):
    EgresadoService(db).eliminar_certificacion(current_user.id_usuario, item_id)


@router.get("/me/habilidades", response_model=list[HabilidadResponse])
def listar_habilidades(current_user: CurrentUser = Depends(_solo_egresado), db: Session = Depends(get_db)):
    return EgresadoService(db).listar_habilidades(current_user.id_usuario)


@router.put("/me/habilidades", response_model=list[HabilidadResponse])
def actualizar_habilidades(
    data: HabilidadesRequest, current_user: CurrentUser = Depends(_solo_egresado), db: Session = Depends(get_db)
):
    return EgresadoService(db).actualizar_habilidades(current_user.id_usuario, data)
