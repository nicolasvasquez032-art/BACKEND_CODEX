import json
import logging
from uuid import UUID
from fastapi import WebSocket
from starlette.websockets import WebSocketState

from infrastructure.config import settings

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Gestor de conexiones WebSocket.
    
    Cumplimiento de The Twelve-Factor App (Factor VI: Procesos sin estado):
    Mantiene las conexiones locales de la instancia actual y provee ganchos
    de mensajería distribuida (Pub/Sub) para ambientes multi-instancia en la nube.
    """

    def __init__(self):
        # Mapeo de user_id a su conexión activa en esta instancia
        self.active_connections: dict[UUID, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: UUID):
        if websocket.client_state != WebSocketState.CONNECTED:
            await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"Usuario {user_id} conectado vía WebSocket (Instancia local).")

    def disconnect(self, user_id: UUID):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"Usuario {user_id} desconectado de WebSocket.")

    async def send_personal_message(self, message: dict, user_id: UUID):
        """Envía un mensaje al usuario si está conectado localmente.
        Si está configurado un broker distribuido (Redis), se publica al canal común."""
        websocket = self.active_connections.get(user_id)
        if websocket:
            try:
                await websocket.send_text(json.dumps(message, default=str))
                return
            except Exception as e:
                logger.error(f"Error al enviar mensaje WS a {user_id}: {e}")
                self.disconnect(user_id)

        # Si el usuario no está en la memoria de esta réplica
        if settings.redis_url:
            await self._publish_to_distributed_broker(message, user_id)
        else:
            logger.debug(f"Usuario {user_id} no está conectado a esta instancia.")

    async def _publish_to_distributed_broker(self, message: dict, user_id: UUID):
        """Publica el mensaje al broker distribuido para entrega en otras réplicas (Factor VI)."""
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(settings.redis_url)
            payload = json.dumps({"target_user_id": str(user_id), "data": message})
            await r.publish("talentmatch_chat_events", payload)
            await r.close()
        except ImportError:
            logger.warning("Librería redis no disponible; omisión de broadcast distribuido.")
        except Exception as e:
            logger.warning(f"Error al publicar en broker distribuido: {e}")


manager = ConnectionManager()
