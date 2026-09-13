from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from domain.entities.user import User
from infrastructure.adapters.persistence.database import get_session
from infrastructure.adapters.persistence.notificacion_repository import SqlAlchemyNotificacionRepository
from application.use_cases.register_device_token import RegisterDeviceTokenUseCase
from application.use_cases.get_notificaciones import GetNotificacionesUseCase
from application.use_cases.mark_notificacion_read import MarkNotificacionReadUseCase
from infrastructure.api.dependencies import get_current_user

router = APIRouter(prefix="/notificaciones", tags=["notificaciones"])


class DeviceTokenRequest(BaseModel):
    token: str
    dispositivo_info: str | None = None


class NotificacionResponse(BaseModel):
    id: UUID
    tipo: str
    mensaje: str
    leido: bool
    creado_en: str


@router.post("/token-dispositivo", status_code=status.HTTP_200_OK)
async def registrar_token_dispositivo(
    request: DeviceTokenRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    repo = SqlAlchemyNotificacionRepository(session)
    use_case = RegisterDeviceTokenUseCase(repo)
    
    await use_case.execute(
        usuario_id=current_user.id,
        token=request.token,
        dispositivo_info=request.dispositivo_info
    )
    return {"message": "Token de dispositivo registrado exitosamente"}


@router.get("/usuario/{usuario_id}", response_model=list[NotificacionResponse])
async def obtener_notificaciones(
    usuario_id: UUID,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if current_user.id != usuario_id:
        raise HTTPException(status_code=403, detail="No autorizado para ver estas notificaciones")

    repo = SqlAlchemyNotificacionRepository(session)
    use_case = GetNotificacionesUseCase(repo)
    
    notificaciones = await use_case.execute(usuario_id=usuario_id, limit=limit, offset=offset)
    
    return [
        NotificacionResponse(
            id=n.id,
            tipo=n.tipo,
            mensaje=n.mensaje,
            leido=n.leido,
            creado_en=n.creado_en.isoformat()
        )
        for n in notificaciones
    ]


@router.patch("/{notificacion_id}/leida", status_code=status.HTTP_200_OK)
async def marcar_notificacion_leida(
    notificacion_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    repo = SqlAlchemyNotificacionRepository(session)
    use_case = MarkNotificacionReadUseCase(repo)
    
    await use_case.execute(notificacion_id=notificacion_id)
    return {"message": "Notificación marcada como leída"}
