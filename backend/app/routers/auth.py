from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.common.request_context import get_client_ip
from app.core.database import get_db
from app.schemas.auth import LoginRequest, MessageResponse, RegistroEgresadoRequest, RegistroEmpresaRequest, TokenResponse
from app.services.auditoria_service import AuditoriaService
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/registro/egresado", response_model=MessageResponse, status_code=201)
def registrar_egresado(data: RegistroEgresadoRequest, request: Request, db: Session = Depends(get_db)) -> MessageResponse:
    usuario = AuthService(db).registrar_egresado(data)
    AuditoriaService(db).registrar(
        modulo="auth", accion="registro_egresado", usuario_id=usuario.id, ip=get_client_ip(request)
    )
    db.commit()
    return MessageResponse(detail="Registro exitoso. Revisa tu correo para verificar la cuenta.")


@router.post("/registro/empresa", response_model=MessageResponse, status_code=201)
def registrar_empresa(data: RegistroEmpresaRequest, request: Request, db: Session = Depends(get_db)) -> MessageResponse:
    usuario = AuthService(db).registrar_empresa(data)
    AuditoriaService(db).registrar(
        modulo="auth", accion="registro_empresa", usuario_id=usuario.id, ip=get_client_ip(request)
    )
    db.commit()
    return MessageResponse(detail="Solicitud de registro recibida. Queda pendiente de autorización.")


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    token = AuthService(db).login(data.correo, data.password)
    AuditoriaService(db).registrar(modulo="auth", accion="login", ip=get_client_ip(request))
    db.commit()
    return token
