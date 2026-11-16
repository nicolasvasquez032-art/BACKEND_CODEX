import asyncio
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
        self._listener_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    async def start_redis_listener(self):
        """Inicia el consumidor distribuido en segundo plano si Redis está activo."""
        if not settings.redis_url:
            return
        if self._listener_task is None or self._listener_task.done():
            self._stop_event.clear()
            self._listener_task = asyncio.create_task(self._listen_to_redis())
            logger.info("Suscripción distribuida a Redis Pub/Sub iniciada para WebSockets.")

    async def stop_redis_listener(self):
        """Detiene el consumidor de Redis de manera elegante al apagar el servicio."""
        self._stop_event.set()
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except (asyncio.CancelledError, Exception):
                pass
            self._listener_task = None
            logger.info("Suscripción distribuida a Redis Pub/Sub detenida.")

    async def _listen_to_redis(self):
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(settings.redis_url)
            pubsub = r.pubsub()
            await pubsub.subscribe("talentmatch_chat_events")
            while not self._stop_event.is_set():
                try:
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message and message.get("type") == "message":
                        data_str = message.get("data")
                        if isinstance(data_str, bytes):
                            data_str = data_str.decode("utf-8")
                        payload = json.loads(data_str)
                        target_id_str = payload.get("target_user_id")
                        msg_data = payload.get("data")
                        if target_id_str and msg_data:
                            target_uuid = UUID(target_id_str)
                            ws = self.active_connections.get(target_uuid)
                            if ws:
                                await ws.send_text(json.dumps(msg_data, default=str))
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.debug(f"Error procesando mensaje Redis Pub/Sub: {e}")
                    await asyncio.sleep(0.5)
            await pubsub.unsubscribe("talentmatch_chat_events")
            await pubsub.close()
            await r.close()
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Error en listener Redis Pub/Sub: {e}")

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
