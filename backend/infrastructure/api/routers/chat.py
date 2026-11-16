import re
import uuid
from datetime import datetime, UTC
from typing import List, Optional
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status, HTTPException
from jwt.exceptions import PyJWTError
from pydantic import BaseModel
from sqlalchemy import select, or_, and_, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.user import User
from infrastructure.adapters.persistence.database import get_session, session_factory
from infrastructure.adapters.persistence.models import (
    MessageModel,
    ChatRoomModel,
    CandidateProfileModel,
    UserModel,
    NotificacionModel,
    DeviceTokenModel,
)
from infrastructure.adapters.persistence.user_repository import SqlAlchemyUserRepository
from infrastructure.api.dependencies import get_current_user
from infrastructure.api.websockets_manager import manager
from infrastructure.config import settings

router = APIRouter(prefix="/chat", tags=["chat"])


# ─────────────────────────────────────────────────────────────────────────────
# ESQUEMAS PYDANTIC
# ─────────────────────────────────────────────────────────────────────────────

class CreateRoomRequest(BaseModel):
    empresa_id: UUID
    candidato_id: UUID


class RoomResponse(BaseModel):
    id: UUID
    empresa_id: UUID
    candidato_id: UUID


class RoomListItem(BaseModel):
    id: UUID
    other_user_id: UUID
    other_user_name: str
    other_user_role: str
    last_message: Optional[str] = None
    last_message_time: Optional[datetime] = None
    unread_count: int = 0


class MessageResponse(BaseModel):
    id: UUID
    room_id: UUID
    sender_id: UUID
    content: str
    creado_en: datetime
    leido: bool


class SendMessageRequest(BaseModel):
    content: str


class IniciarVideollamadaRequest(BaseModel):
    titulo: str = "Entrevista en Vivo TalentMatch"


class ProgramarEntrevistaRequest(BaseModel):
    titulo: str = "Entrevista Laboral TalentMatch"
    fecha_hora: str  # Fecha y hora legible o ISO (ej. "2026-11-20 10:00 AM")
    notas: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# WEBSOCKET AUTHENTICATION & HANDLER
# ─────────────────────────────────────────────────────────────────────────────

async def _authenticate_websocket(websocket: WebSocket, token: str, user_id: UUID) -> bool:
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
        if token_user_id != user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return False

        async with session_factory() as session:
            repo = SqlAlchemyUserRepository(session)
            user = await repo.find_by_id(token_user_id)
            if user is None:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return False

        return True

    except (PyJWTError, ValueError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return False


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: UUID,
    token: str = Query(..., description="JWT Bearer token para autenticar la conexión WS"),
):
    await websocket.accept()

    if not await _authenticate_websocket(websocket, token, user_id):
        return

    await manager.connect(websocket, user_id)
    try:
        async with session_factory() as session:
            while True:
                data = await websocket.receive_json()

                room_id_str = data.get("room_id")
                content = data.get("content")

                if not room_id_str or not content:
                    continue

                room_id = UUID(room_id_str)

                result = await session.execute(select(ChatRoomModel).where(ChatRoomModel.id == room_id))
                room = result.scalar_one_or_none()

                if not room:
                    continue

                if user_id not in (room.candidato_id, room.empresa_id):
                    continue

                recipient_id = room.empresa_id if user_id == room.candidato_id else room.candidato_id

                new_message = MessageModel(
                    room_id=room_id,
                    sender_id=user_id,
                    content=content,
                )
                session.add(new_message)
                await session.commit()
                await session.refresh(new_message)

                message_payload = {
                    "id": str(new_message.id),
                    "room_id": str(new_message.room_id),
                    "sender_id": str(new_message.sender_id),
                    "content": new_message.content,
                    "creado_en": str(new_message.creado_en),
                    "leido": new_message.leido,
                }

                await manager.send_personal_message(message_payload, recipient_id)

    except WebSocketDisconnect:
        manager.disconnect(user_id)


# ─────────────────────────────────────────────────────────────────────────────
# REST ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/room", response_model=RoomResponse)
async def create_or_get_room(
    request: CreateRoomRequest,
    session: AsyncSession = Depends(get_session),
):
    """Crea una sala de conversación o retorna la existente entre empresa y candidato."""
    result = await session.execute(
        select(ChatRoomModel).where(
            or_(
                and_(ChatRoomModel.empresa_id == request.empresa_id, ChatRoomModel.candidato_id == request.candidato_id),
                and_(ChatRoomModel.empresa_id == request.candidato_id, ChatRoomModel.candidato_id == request.empresa_id),
            )
        )
    )
    room = result.scalar_one_or_none()

    if room:
        return RoomResponse(
            id=room.id,
            empresa_id=room.empresa_id,
            candidato_id=room.candidato_id,
        )

    new_room = ChatRoomModel(
        empresa_id=request.empresa_id,
        candidato_id=request.candidato_id,
    )
    session.add(new_room)
    await session.commit()
    await session.refresh(new_room)
    return RoomResponse(
        id=new_room.id,
        empresa_id=new_room.empresa_id,
        candidato_id=new_room.candidato_id,
    )


@router.get("/rooms", response_model=List[RoomListItem])
async def list_user_rooms(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Lista todas las conversaciones activas del usuario con el último mensaje y el nombre del interlocutor."""
    stmt = (
        select(ChatRoomModel)
        .where(
            or_(
                ChatRoomModel.empresa_id == current_user.id,
                ChatRoomModel.candidato_id == current_user.id,
            )
        )
        .order_by(ChatRoomModel.creado_en.desc())
    )
    res = await session.execute(stmt)
    rooms = res.scalars().all()

    items: List[RoomListItem] = []

    for room in rooms:
        is_empresa = (current_user.id == room.empresa_id)
        other_user_id = room.candidato_id if is_empresa else room.empresa_id

        # Obtener información del interlocutor
        other_user_name = "Usuario"
        other_user_role = "Candidato" if is_empresa else "Empresa"

        if is_empresa:
            # El otro es candidato: buscar en perfiles_candidato
            cand_profile_res = await session.execute(
                select(CandidateProfileModel).where(CandidateProfileModel.user_id == other_user_id)
            )
            cand_prof = cand_profile_res.scalar_one_or_none()
            if cand_prof and cand_prof.full_name:
                other_user_name = cand_prof.full_name
            else:
                user_res = await session.execute(select(UserModel).where(UserModel.id == other_user_id))
                u = user_res.scalar_one_or_none()
                other_user_name = u.email.split('@')[0].capitalize() if u else "Candidato"
        else:
            # El otro es empresa: buscar en usuarios
            user_res = await session.execute(select(UserModel).where(UserModel.id == other_user_id))
            empresa_user = user_res.scalar_one_or_none()
            if empresa_user and getattr(empresa_user, "nombre", None) and empresa_user.nombre.strip():
                other_user_name = empresa_user.nombre.strip()
            elif empresa_user and empresa_user.email:
                prefix = empresa_user.email.split('@')[0]
                clean = re.sub(r'[0-9_\.\-]+', ' ', prefix).strip().title()
                other_user_name = clean if clean else "Empresa Reclutadora"
            else:
                other_user_name = "Empresa Reclutadora"

        # Último mensaje de la sala
        msg_stmt = (
            select(MessageModel)
            .where(MessageModel.room_id == room.id)
            .order_by(MessageModel.creado_en.desc())
            .limit(1)
        )
        msg_res = await session.execute(msg_stmt)
        last_msg = msg_res.scalar_one_or_none()

        # Mensajes sin leer
        unread_stmt = (
            select(func.count(MessageModel.id))
            .where(
                MessageModel.room_id == room.id,
                MessageModel.sender_id != current_user.id,
                MessageModel.leido == False,
            )
        )
        unread_res = await session.execute(unread_stmt)
        unread_count = unread_res.scalar() or 0

        # Formatear contenido del último mensaje si es videollamada o entrevista
        display_last_msg = last_msg.content if last_msg else None
        if display_last_msg:
            if display_last_msg.startswith("[VIDEOCALL]:"):
                display_last_msg = "Invitación a videollamada"
            elif display_last_msg.startswith("[INTERVIEW_SCHEDULED]:"):
                parts = display_last_msg.split("|")
                fecha = parts[2] if len(parts) > 2 else ""
                display_last_msg = f"Entrevista programada: {fecha}"

        items.append(
            RoomListItem(
                id=room.id,
                other_user_id=other_user_id,
                other_user_name=other_user_name,
                other_user_role=other_user_role,
                last_message=display_last_msg,
                last_message_time=last_msg.creado_en if last_msg else room.creado_en,
                unread_count=unread_count,
            )
        )

    # Ordenar por fecha del último mensaje
    items.sort(key=lambda x: x.last_message_time or datetime.min.replace(tzinfo=UTC), reverse=True)
    return items


@router.get("/{room_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    room_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Obtiene el historial de mensajes de la sala y marca como leídos los del interlocutor."""
    # Verificar acceso a la sala
    room_res = await session.execute(select(ChatRoomModel).where(ChatRoomModel.id == room_id))
    room = room_res.scalar_one_or_none()
    if not room or current_user.id not in (room.candidato_id, room.empresa_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No perteneces a esta conversación")

    # Marcar como leídos los mensajes que no fueron enviados por mí
    await session.execute(
        update(MessageModel)
        .where(
            MessageModel.room_id == room_id,
            MessageModel.sender_id != current_user.id,
            MessageModel.leido == False,
        )
        .values(leido=True)
    )
    await session.commit()

    result = await session.execute(
        select(MessageModel).where(MessageModel.room_id == room_id).order_by(MessageModel.creado_en.asc())
    )
    messages = result.scalars().all()
    return messages


@router.post("/{room_id}/messages", response_model=MessageResponse)
async def send_message(
    room_id: UUID,
    payload: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Envía un mensaje de texto por HTTP REST y notifica vía WebSocket y push notification."""
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El mensaje no puede estar vacío")

    room_res = await session.execute(select(ChatRoomModel).where(ChatRoomModel.id == room_id))
    room = room_res.scalar_one_or_none()
    if not room or current_user.id not in (room.candidato_id, room.empresa_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No perteneces a esta conversación")

    recipient_id = room.empresa_id if current_user.id == room.candidato_id else room.candidato_id

    new_msg = MessageModel(
        room_id=room_id,
        sender_id=current_user.id,
        content=content,
    )
    session.add(new_msg)

    # Notificación interna
    try:
        sender_type = "La empresa" if current_user.id == room.empresa_id else "El candidato"
        notif = NotificacionModel(
            usuario_id=recipient_id,
            tipo="chat_mensaje",
            mensaje=f"{sender_type} te ha enviado un mensaje.",
            leido=False,
        )
        session.add(notif)
    except Exception:
        pass

    await session.commit()
    await session.refresh(new_msg)

    message_payload = {
        "id": str(new_msg.id),
        "room_id": str(new_msg.room_id),
        "sender_id": str(new_msg.sender_id),
        "content": new_msg.content,
        "creado_en": str(new_msg.creado_en),
        "leido": new_msg.leido,
    }

    # Transmitir por WebSocket en vivo al destinatario
    await manager.send_personal_message(message_payload, recipient_id)

    # Push Notification FCM
    try:
        from infrastructure.adapters.fcm_adapter import RealFcmAdapter
        fcm = RealFcmAdapter()
        tokens_res = await session.execute(
            select(DeviceTokenModel.token).where(DeviceTokenModel.usuario_id == recipient_id)
        )
        for dev_token in tokens_res.scalars().all():
            await fcm.send_notification(
                token=dev_token,
                title="Nuevo mensaje en TalentMatch",
                body=content[:80],
                data={"tipo": "chat", "room_id": str(room_id)},
            )
    except Exception:
        pass

    return new_msg


@router.post("/{room_id}/videollamada")
async def iniciar_videollamada_chat(
    room_id: UUID,
    payload: IniciarVideollamadaRequest = IniciarVideollamadaRequest(),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Inicia una sala de videollamada inmediata para la conversación."""
    result = await session.execute(select(ChatRoomModel).where(ChatRoomModel.id == room_id))
    room = result.scalar_one_or_none()
    if not room or current_user.id not in (room.candidato_id, room.empresa_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No perteneces a esta conversación")

    if current_user.id != room.empresa_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo la empresa reclutadora tiene autorización para iniciar videollamadas de entrevista."
        )

    call_code = uuid.uuid4().hex[:10]
    room_name = f"TalentMatch-Call-{call_code}"
    meeting_url = f"https://meet.jit.si/{room_name}#config.prejoinPageEnabled=false"
    titulo = payload.titulo if payload and payload.titulo else "Entrevista en Vivo TalentMatch"
    content = f"[VIDEOCALL]:{meeting_url}|{titulo}"

    msg = MessageModel(
        room_id=room_id,
        sender_id=current_user.id,
        content=content,
    )
    session.add(msg)

    # Registrar notificación interna para el candidato
    try:
        notif = NotificacionModel(
            usuario_id=room.candidato_id,
            tipo="videollamada",
            mensaje=f"Invitación a videollamada de entrevista: {titulo}",
            leido=False,
        )
        session.add(notif)
    except Exception:
        pass

    await session.commit()
    await session.refresh(msg)

    message_payload = {
        "id": str(msg.id),
        "room_id": str(msg.room_id),
        "sender_id": str(msg.sender_id),
        "content": msg.content,
        "creado_en": str(msg.creado_en),
        "leido": msg.leido,
    }

    await manager.send_personal_message(message_payload, room.candidato_id)
    await manager.send_personal_message(message_payload, current_user.id)

    # Push FCM
    try:
        from infrastructure.adapters.fcm_adapter import RealFcmAdapter
        fcm = RealFcmAdapter()
        tokens_res = await session.execute(
            select(DeviceTokenModel.token).where(DeviceTokenModel.usuario_id == room.candidato_id)
        )
        for dev_token in tokens_res.scalars().all():
            await fcm.send_notification(
                token=dev_token,
                title="Invitación a Videollamada",
                body=f"La empresa te ha invitado a una entrevista en vivo: {titulo}",
                data={
                    "tipo": "videollamada",
                    "meeting_url": meeting_url,
                    "room_id": str(room.id),
                },
            )
    except Exception:
        pass

    return {
        "meeting_url": meeting_url,
        "room_name": room_name,
        "message": message_payload,
    }


@router.post("/{room_id}/programar-entrevista")
async def programar_entrevista_chat(
    room_id: UUID,
    payload: ProgramarEntrevistaRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Programa una entrevista laboral con fecha y hora específicas mediante calendario."""
    result = await session.execute(select(ChatRoomModel).where(ChatRoomModel.id == room_id))
    room = result.scalar_one_or_none()
    if not room or current_user.id not in (room.candidato_id, room.empresa_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No perteneces a esta conversación")

    if current_user.id != room.empresa_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo la empresa empleadora tiene autorización para programar fechas de entrevista."
        )

    call_code = uuid.uuid4().hex[:10]
    room_name = f"TalentMatch-Entrevista-{call_code}"
    meeting_url = f"https://meet.jit.si/{room_name}#config.prejoinPageEnabled=false"
    titulo = payload.titulo.strip() if payload.titulo else "Entrevista Laboral"
    fecha_hora = payload.fecha_hora.strip()
    notas = (payload.notas or "").strip()

    content = f"[INTERVIEW_SCHEDULED]:{meeting_url}|{titulo}|{fecha_hora}|{notas}"

    msg = MessageModel(
        room_id=room_id,
        sender_id=current_user.id,
        content=content,
    )
    session.add(msg)

    # Notificación interna
    try:
        notif = NotificacionModel(
            usuario_id=room.candidato_id,
            tipo="entrevista_programada",
            mensaje=f"Entrevista programada para el {fecha_hora}: {titulo}",
            leido=False,
        )
        session.add(notif)
    except Exception:
        pass

    await session.commit()
    await session.refresh(msg)

    message_payload = {
        "id": str(msg.id),
        "room_id": str(msg.room_id),
        "sender_id": str(msg.sender_id),
        "content": msg.content,
        "creado_en": str(msg.creado_en),
        "leido": msg.leido,
    }

    await manager.send_personal_message(message_payload, room.candidato_id)
    await manager.send_personal_message(message_payload, current_user.id)

    # Push Notification FCM
    try:
        from infrastructure.adapters.fcm_adapter import RealFcmAdapter
        fcm = RealFcmAdapter()
        tokens_res = await session.execute(
            select(DeviceTokenModel.token).where(DeviceTokenModel.usuario_id == room.candidato_id)
        )
        for dev_token in tokens_res.scalars().all():
            await fcm.send_notification(
                token=dev_token,
                title="Entrevista Programada",
                body=f"{titulo} agendada para el {fecha_hora}",
                data={
                    "tipo": "entrevista_programada",
                    "meeting_url": meeting_url,
                    "room_id": str(room.id),
                    "fecha_hora": fecha_hora,
                },
            )
    except Exception:
        pass

    return {
        "meeting_url": meeting_url,
        "room_name": room_name,
        "titulo": titulo,
        "fecha_hora": fecha_hora,
        "message": message_payload,
    }
