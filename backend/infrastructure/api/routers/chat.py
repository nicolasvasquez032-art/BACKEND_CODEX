from uuid import UUID

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from infrastructure.adapters.persistence.database import get_session, session_factory
from infrastructure.adapters.persistence.models import MessageModel, ChatRoomModel
from infrastructure.adapters.persistence.user_repository import SqlAlchemyUserRepository
from infrastructure.api.websockets_manager import manager
from infrastructure.config import settings

router = APIRouter(prefix="/chat", tags=["chat"])


async def _authenticate_websocket(websocket: WebSocket, token: str, user_id: UUID) -> bool:
    """Valida el JWT y verifica que el user_id del path coincida con el del token.

    Cierra el WebSocket con 1008 (Policy Violation) si la autenticación falla.
    Retorna True si la autenticación es exitosa.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        token_user_id_str: str | None = payload.get("sub")
        if token_user_id_str is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return False

        token_user_id = UUID(token_user_id_str)

        # El user_id del path debe coincidir con el del JWT para evitar suplantación
        if token_user_id != user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return False

        # Verificar que el usuario existe en la BD
        async with session_factory() as session:
            repo = SqlAlchemyUserRepository(session)
            user = await repo.find_by_id(token_user_id)
            if user is None:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return False

        return True

    except (JWTError, ValueError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return False


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: UUID,
    token: str = Query(..., description="JWT Bearer token para autenticar la conexión WS"),
):
    """WebSocket de chat en tiempo real.

    Requiere autenticación: pasar el JWT como query param `?token=<access_token>`.
    El user_id del path debe coincidir con el 'sub' del JWT.
    """
    await websocket.accept()

    # Autenticar antes de procesar mensajes
    if not await _authenticate_websocket(websocket, token, user_id):
        return  # La conexión ya fue cerrada en _authenticate_websocket

    await manager.connect(websocket, user_id)
    try:
        async with session_factory() as session:
            while True:
                # When a message is received from the client
                data = await websocket.receive_json()

                # data should contain "room_id" and "content"
                room_id_str = data.get("room_id")
                content = data.get("content")

                if not room_id_str or not content:
                    continue

                room_id = UUID(room_id_str)

                # Fetch the room to find the other participant
                result = await session.execute(select(ChatRoomModel).where(ChatRoomModel.id == room_id))
                room = result.scalar_one_or_none()

                if not room:
                    continue

                # Verify the authenticated user belongs to this room
                if user_id not in (room.candidato_id, room.empresa_id):
                    continue  # Silently ignore messages for rooms the user doesn't belong to

                # Determine who is the recipient
                recipient_id = room.empresa_id if user_id == room.candidato_id else room.candidato_id

                # Save the message to DB
                new_message = MessageModel(
                    room_id=room_id,
                    sender_id=user_id,
                    content=content,
                )
                session.add(new_message)
                await session.commit()
                await session.refresh(new_message)

                # Format the message to send
                message_payload = {
                    "id": str(new_message.id),
                    "room_id": str(new_message.room_id),
                    "sender_id": str(new_message.sender_id),
                    "content": new_message.content,
                    "creado_en": str(new_message.creado_en),
                    "leido": new_message.leido,
                }

                # Send to recipient (if they are online)
                await manager.send_personal_message(message_payload, recipient_id)

                # Acknowledge the sender that the message was processed
                await manager.send_personal_message(message_payload, user_id)

    except WebSocketDisconnect:
        manager.disconnect(user_id)


from pydantic import BaseModel
from typing import List
from datetime import datetime


class CreateRoomRequest(BaseModel):
    empresa_id: UUID
    candidato_id: UUID


class MessageResponse(BaseModel):
    id: UUID
    room_id: UUID
    sender_id: UUID
    content: str
    creado_en: datetime
    leido: bool


@router.post("/room")
async def create_or_get_room(
    request: CreateRoomRequest,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(ChatRoomModel).where(
            ChatRoomModel.empresa_id == request.empresa_id,
            ChatRoomModel.candidato_id == request.candidato_id,
        )
    )
    room = result.scalar_one_or_none()

    if room:
        return {
            "id": str(room.id),
            "empresa_id": str(room.empresa_id),
            "candidato_id": str(room.candidato_id),
        }

    new_room = ChatRoomModel(
        empresa_id=request.empresa_id,
        candidato_id=request.candidato_id,
    )
    session.add(new_room)
    await session.commit()
    await session.refresh(new_room)
    return {
        "id": str(new_room.id),
        "empresa_id": str(new_room.empresa_id),
        "candidato_id": str(new_room.candidato_id),
    }


@router.get("/{room_id}/messages", response_model=List[MessageResponse])
async def get_messages(room_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(MessageModel).where(MessageModel.room_id == room_id).order_by(MessageModel.creado_en.asc())
    )
    messages = result.scalars().all()
    return messages
