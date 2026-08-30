from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.common.exceptions import UnauthorizedException
from app.common.request_context import get_client_ip
from app.core.database import get_db
from app.features.auth.schema import (
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegistroEgresadoRequest,
    RegistroEmpresaRequest,
    TokenResponse,
)
from app.features.bitacora.service import BitacoraService
from app.features.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/registro/egresado", response_model=MessageResponse, status_code=201)
def registrar_egresado(data: RegistroEgresadoRequest, request: Request, db: Session = Depends(get_db)) -> MessageResponse:
    usuario = AuthService(db).registrar_egresado(data)
    BitacoraService(db).registrar(
        modulo="auth", accion="registro_egresado", usuario_id=usuario.id, ip=get_client_ip(request)
    )
    db.commit()
    return MessageResponse(detail="Registro exitoso. Revisa tu correo para verificar la cuenta.")


@router.post("/registro/empresa", response_model=MessageResponse, status_code=201)
def registrar_empresa(data: RegistroEmpresaRequest, request: Request, db: Session = Depends(get_db)) -> MessageResponse:
    usuario = AuthService(db).registrar_empresa(data)
    BitacoraService(db).registrar(
        modulo="auth", accion="registro_empresa", usuario_id=usuario.id, ip=get_client_ip(request)
    )
    db.commit()
    return MessageResponse(detail="Solicitud de registro recibida. Queda pendiente de autorización.")


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    ip = get_client_ip(request)
    try:
        token, usuario = AuthService(db).login(data.correo, data.password)
    except UnauthorizedException:
        BitacoraService(db).registrar(
            modulo="auth",
            accion="login_fallido",
            ip=ip,
            detalles=f"correo={data.correo}",
            resultado=False,
        )
        db.commit()
        raise

    BitacoraService(db).registrar(modulo="auth", accion="login", usuario_id=usuario.id, ip=ip)
    db.commit()
    return token


@router.post("/refresh", response_model=TokenResponse)
def refrescar_token(data: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return AuthService(db).refrescar_token(data.refresh_token)
