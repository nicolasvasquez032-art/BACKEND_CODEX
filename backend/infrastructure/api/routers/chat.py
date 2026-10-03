from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from infrastructure.adapters.persistence.database import get_session
from infrastructure.adapters.persistence.models import MessageModel, ChatRoomModel
from infrastructure.api.websockets_manager import manager

router = APIRouter(prefix="/chat", tags=["chat"])

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: UUID, session: AsyncSession = Depends(get_session)):
    await manager.connect(websocket, user_id)
    try:
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
                
            # Determine who is the recipient
            recipient_id = room.empresa_id if user_id == room.candidato_id else room.candidato_id
            
            # Save the message to DB
            new_message = MessageModel(
                room_id=room_id,
                sender_id=user_id,
                content=content
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
                "leido": new_message.leido
            }
            
            # Send to recipient (if they are online)
            await manager.send_personal_message(message_payload, recipient_id)
            
            # Optionally, acknowledge the sender that the message was processed
            await manager.send_personal_message(message_payload, user_id)
            
    except WebSocketDisconnect:
        manager.disconnect(user_id)
