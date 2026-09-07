import uuid
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.features.vacantes.schema import (
    FiltrosDisponiblesResponse,
    VacanteCambioEstadoRequest,
    VacanteCreateRequest,
    VacanteDetalleBusquedaResponse,
    VacantePaginadaResponse,
    VacanteResponse,
    VacanteUpdateRequest,
    VacantesBuscadasResponse,
)
from app.features.vacantes.service import VacanteService
from app.models.vacante import ScreeningOption, ScreeningQuestion
from app.security.dependencies import CurrentUser, get_current_user, get_current_user_optional, require_roles

router = APIRouter(prefix="/vacantes", tags=["vacantes"])


class ScreeningOptionSchema(BaseModel):
    id: uuid.UUID
    option_text: str


class ScreeningQuestionSchema(BaseModel):
    id: uuid.UUID
    question_text: str
    question_type: str
    is_required: bool
    options: List[ScreeningOptionSchema] = []

    class Config:
        from_attributes = True


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
    "/buscar",
    response_model=VacantesBuscadasResponse,
    summary="Búsqueda avanzada de vacantes con afinidad (HU-13)",
    description=(
        "Busca y filtra vacantes publicadas y vigentes, con filtros por carrera, categoría, ciudad, "
        "modalidad, jornada, seniority y rango salarial. Si el solicitante está autenticado como "
        "egresado, calcula un porcentaje de afinidad según su carrera y habilidades registradas."
    ),
)
def buscar_vacantes(
    q: str | None = Query(None, description="Búsqueda por palabra clave en título o descripción"),
    carrera_id: uuid.UUID | None = Query(None, description="Filtro por carrera o campo de estudio"),
    categoria_id: uuid.UUID | None = Query(None, description="Filtro por categoría de empleo"),
    ciudad: str | None = Query(None, description="Filtro por ciudad"),
    modalidad: str | None = Query(None, description="Filtro por modalidad (onsite, remote, hybrid)"),
    jornada: str | None = Query(None, description="Filtro por jornada (permanent, part_time, internship, etc.)"),
    seniority: str | None = Query(None, description="Filtro por nivel de experiencia"),
    salario_min: Decimal | None = Query(None, description="Rango salarial mínimo"),
    salario_max: Decimal | None = Query(None, description="Rango salarial máximo"),
    ordenar_por: str = Query("fecha", description="Criterio de ordenamiento: 'fecha' o 'afinidad'"),
    limit: int = Query(20, ge=1, le=100, description="Cantidad de resultados por página"),
    offset: int = Query(0, ge=0, description="Desplazamiento para paginación"),
    current_user: CurrentUser | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    usuario_id = current_user.id_usuario if current_user else None
    return VacanteService(db).buscar_vacantes(
        q=q,
        carrera_id=carrera_id,
        categoria_id=categoria_id,
        ciudad=ciudad,
        modalidad=modalidad,
        jornada=jornada,
        seniority=seniority,
        salario_min=salario_min,
        salario_max=salario_max,
        ordenar_por=ordenar_por,
        limit=limit,
        offset=offset,
        usuario_id=usuario_id,
    )


@router.get(
    "/buscar/filtros",
    response_model=FiltrosDisponiblesResponse,
    summary="Opciones disponibles para los filtros de búsqueda (HU-13)",
    description="Retorna ciudades, modalidades, jornadas, categorías, carreras y rango salarial vigentes entre las vacantes publicadas.",
)
def obtener_filtros_disponibles_busqueda(db: Session = Depends(get_db)):
    return VacanteService(db).obtener_filtros_disponibles()


@router.get(
    "/buscar/{vacante_id}",
    response_model=VacanteDetalleBusquedaResponse,
    summary="Detalle enriquecido de una vacante para la búsqueda (HU-13)",
    description="Como el detalle público, pero incluye afinidad calculada y datos de contacto de la empresa. Incrementa el contador de vistas.",
)
def obtener_detalle_busqueda_vacante(
    vacante_id: uuid.UUID,
    current_user: CurrentUser | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    usuario_id = current_user.id_usuario if current_user else None
    return VacanteService(db).obtener_detalle_busqueda(vacante_id, usuario_id=usuario_id)


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


@router.get(
    "/{vacante_id}/preguntas",
    response_model=List[ScreeningQuestionSchema],
    summary="Consultar preguntas de filtro de una vacante",
    description="Retorna las preguntas de filtro (screening) configuradas para la vacante, usadas al postularse (HU-14).",
)
def obtener_preguntas_vacante(vacante_id: uuid.UUID, db: Session = Depends(get_db)):
    preguntas = (
        db.query(ScreeningQuestion)
        .filter(ScreeningQuestion.job_posting_id == vacante_id)
        .order_by(ScreeningQuestion.position)
        .all()
    )

    resultado = []
    for pregunta in preguntas:
        opciones = (
            db.query(ScreeningOption)
            .filter(ScreeningOption.question_id == pregunta.id)
            .order_by(ScreeningOption.position)
            .all()
        )
        resultado.append(
            {
                "id": pregunta.id,
                "question_text": pregunta.question_text,
                "question_type": pregunta.question_type,
                "is_required": pregunta.is_required,
                "options": [{"id": o.id, "option_text": o.option_text} for o in opciones],
            }
        )
    return resultado
