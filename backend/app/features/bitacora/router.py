import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.features.bitacora.schema import BitacoraLogResponse
from app.security.dependencies import require_roles
from app.features.bitacora.service import BitacoraService

router = APIRouter(prefix="/bitacora", tags=["bitacora"])

_solo_admin = require_roles("platform_admin", "moderator")


@router.get("", response_model=list[BitacoraLogResponse], dependencies=[Depends(_solo_admin)])
def listar_bitacora(
    usuario_id: uuid.UUID | None = None,
    modulo: str | None = None,
    accion: str | None = None,
    fecha_desde: datetime | None = None,
    fecha_hasta: datetime | None = None,
    db: Session = Depends(get_db),
):
    return BitacoraService(db).listar(
        usuario_id=usuario_id,
        modulo=modulo,
        accion=accion,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )


@router.get("/export/excel", dependencies=[Depends(_solo_admin)])
def exportar_excel(
    usuario_id: uuid.UUID | None = None,
    modulo: str | None = None,
    accion: str | None = None,
    fecha_desde: datetime | None = None,
    fecha_hasta: datetime | None = None,
    db: Session = Depends(get_db),
):
    service = BitacoraService(db)
    logs = service.listar(
        usuario_id=usuario_id, modulo=modulo, accion=accion, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta
    )
    contenido = service.exportar_excel(logs)
    return Response(
        content=contenido,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=bitacora.xlsx"},
    )


@router.get("/export/pdf", dependencies=[Depends(_solo_admin)])
def exportar_pdf(
    usuario_id: uuid.UUID | None = None,
    modulo: str | None = None,
    accion: str | None = None,
    fecha_desde: datetime | None = None,
    fecha_hasta: datetime | None = None,
    db: Session = Depends(get_db),
):
    service = BitacoraService(db)
    logs = service.listar(
        usuario_id=usuario_id, modulo=modulo, accion=accion, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta
    )
    contenido = service.exportar_pdf(logs)
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=bitacora.pdf"},
    )
