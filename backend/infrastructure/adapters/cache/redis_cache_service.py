"""Servicio de Caché en Memoria con Redis para TalentMatch.

Proporciona almacenamiento en caché distribuido de alto rendimiento con:
- Fallback tolerante a fallos (Graceful Degradation): Si Redis no está disponible,
  la aplicación sigue operando contra la base de datos sin lanzar excepciones 500.
- Invalidación atómica O(1) basada en versiones para colecciones masivas como Vacantes.
- Soporte asíncrono con connection pooling no bloqueante.
"""
from typing import Any
import json
from loguru import logger
import redis.asyncio as aioredis

from infrastructure.config import settings


class RedisCacheService:
    _instance: "RedisCacheService | None" = None
    _client: aioredis.Redis | None = None
    _is_available: bool = True

    def __init__(self, redis_url: str | None = None) -> None:
        self.redis_url = redis_url or settings.redis_url
        if self.redis_url:
            try:
                self._client = aioredis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=2.0,
                    socket_timeout=2.0,
                )
                logger.info("Adaptador de Caché Redis inicializado.")
            except Exception as e:
                logger.warning(f"No se pudo conectar al servidor Redis ({e}). Modo fallback activo.")
                self._client = None
                self._is_available = False
        else:
            self._client = None
            self._is_available = False

    @classmethod
    def get_instance(cls) -> "RedisCacheService":
        if cls._instance is None:
            cls._instance = RedisCacheService()
        return cls._instance

    @property
    def is_available(self) -> bool:
        return self._client is not None and self._is_available

    async def get(self, key: str) -> str | None:
        if not self.is_available:
            return None
        try:
            return await self._client.get(key)
        except Exception as e:
            logger.debug(f"Error al leer de Redis ({key}): {e}")
            return None

    async def set(self, key: str, value: str, ttl: int = 60) -> bool:
        if not self.is_available:
            return False
        try:
            await self._client.set(key, value, ex=ttl)
            return True
        except Exception as e:
            logger.debug(f"Error al escribir en Redis ({key}): {e}")
            return False

    async def get_json(self, key: str) -> Any | None:
        data = await self.get(key)
        if data is None:
            return None
        try:
            return json.loads(data)
        except Exception:
            return None

    async def set_json(self, key: str, value: Any, ttl: int = 60) -> bool:
        try:
            payload = json.dumps(value, default=str)
            return await self.set(key, payload, ttl=ttl)
        except Exception as e:
            logger.debug(f"Error serializando JSON para Redis: {e}")
            return False

    async def get_vacantes_version(self) -> int:
        """Obtiene la versión actual de la colección de vacantes (O(1))."""
        val = await self.get("vacantes:cache_version")
        if val is None:
            return 1
        try:
            return int(val)
        except ValueError:
            return 1

    async def invalidate_vacantes_cache(self) -> None:
        """Invalida instantáneamente todo el caché de vacantes de forma atómica O(1)."""
        if not self.is_available:
            return
        try:
            await self._client.incr("vacantes:cache_version")
            logger.info("Caché de vacantes invalidado exitosamente mediante incremento de versión.")
        except Exception as e:
            logger.debug(f"Error al invalidar caché de vacantes: {e}")

    async def close(self) -> None:
        if self._client:
            await self._client.close()
