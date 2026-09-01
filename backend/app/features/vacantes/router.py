import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.features.vacantes.schema import (
    VacanteCambioEstadoRequest,
    VacanteCreateRequest,
    VacantePaginadaResponse,
    VacanteResponse,
    VacanteUpdateRequest,
)
from app.features.vacantes.service import VacanteService
from app.security.dependencies import CurrentUser, get_current_user, require_roles

router = APIRouter(prefix="/vacantes", tags=["vacantes"])


@router.post(
    "",
    response_model=VacanteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Publicar o registrar una vacante",
    description=(
        "Permite a una empresa crear una nueva vacante. "
        "Si la empresa no está verificada por la institución, la vacante se guardará forzosamente como borrador (draft)."
    ),
)
def crear_vacante(
    payload: VacanteCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("empresa", "platform_admin")),
):
    ip_address = request.client.host if request.client else None
    return VacanteService(db).crear_vacante(payload, current_user, ip_address=ip_address)


@router.get(
    "/mis-vacantes",
    response_model=VacantePaginadaResponse,
    summary="Listar las vacantes de la empresa autenticada",
    description="Retorna el listado paginado de todas las vacantes pertenecientes a la empresa del usuario actual.",
)
def listar_mis_vacantes(
    estado: str | None = Query(default=None, description="Filtrar por estado: draft, published, paused, closed"),
    page: int = Query(default=1, ge=1, description="Número de página"),
    page_size: int = Query(default=10, ge=1, le=100, description="Tamaño de página"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("empresa", "platform_admin")),
):
    return VacanteService(db).listar_mis_vacantes(
        current_user=current_user,
        estado=estado,
        page=page,
        page_size=page_size,
    )


@router.get(
    "",
    response_model=VacantePaginadaResponse,
    summary="Explorar vacantes publicadas",
    description="Lista pública o para candidatos con todas las vacantes en estado 'published' aplicando filtros opcionales.",
)
def listar_vacantes_publicas(
    q: str | None = Query(default=None, description="Búsqueda por texto en título o descripción"),
    category_id: uuid.UUID | None = Query(default=None, description="ID de la categoría de empleo"),
    city: str | None = Query(default=None, description="Ciudad de la vacante"),
    work_modality: str | None = Query(default=None, description="Modalidad: onsite, remote, hybrid"),
    seniority_level: str | None = Query(default=None, description="Seniority: internship, junior, mid, senior, lead"),
    employment_type: str | None = Query(default=None, description="Tipo: permanent, temporary, project, internship, freelance"),
    salary_min: Decimal | None = Query(default=None, ge=0, description="Salario mínimo pretendido"),
    page: int = Query(default=1, ge=1, description="Número de página"),
    page_size: int = Query(default=10, ge=1, le=100, description="Tamaño de página"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return VacanteService(db).listar_publicas(
        q=q,
        category_id=category_id,
        city=city,
        work_modality=work_modality,
        seniority_level=seniority_level,
        employment_type=employment_type,
        salary_min=salary_min,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{vacante_id}",
    response_model=VacanteResponse,
    summary="Consultar detalle de una vacante",
    description="Retorna la información completa de una vacante si está publicada o si el usuario es su propietario.",
)
def obtener_detalle_vacante(
    vacante_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return VacanteService(db).obtener_detalle(vacante_id, current_user=current_user)


@router.put(
    "/{vacante_id}",
    response_model=VacanteResponse,
    summary="Actualizar información de una vacante",
    description="Permite a la empresa propietaria editar los datos y habilidades de su vacante.",
)
def actualizar_vacante(
    vacante_id: uuid.UUID,
    payload: VacanteUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("empresa", "platform_admin")),
):
    ip_address = request.client.host if request.client else None
    return VacanteService(db).actualizar_vacante(
        vacante_id=vacante_id,
        payload=payload,
        current_user=current_user,
        ip_address=ip_address,
    )


@router.patch(
    "/{vacante_id}/estado",
    response_model=VacanteResponse,
    summary="Cambiar estado del ciclo de vida de una vacante",
    description="Permite a la empresa cambiar el estado entre draft, published, paused o closed.",
)
def cambiar_estado_vacante(
    vacante_id: uuid.UUID,
    payload: VacanteCambioEstadoRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("empresa", "platform_admin")),
):
    ip_address = request.client.host if request.client else None
    return VacanteService(db).cambiar_estado(
        vacante_id=vacante_id,
        payload=payload,
        current_user=current_user,
        ip_address=ip_address,
    )


@router.delete(
    "/{vacante_id}",
    summary="Eliminar una vacante",
    description="Permite a la empresa eliminar definitivamente su vacante.",
)
def eliminar_vacante(
    vacante_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("empresa", "platform_admin")),
):
    ip_address = request.client.host if request.client else None
    return VacanteService(db).eliminar_vacante(
        vacante_id=vacante_id,
        current_user=current_user,
        ip_address=ip_address,
    )
