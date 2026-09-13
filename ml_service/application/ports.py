from typing import Protocol
from uuid import UUID

from domain.entities import Recomendacion


class EmbeddingModelPort(Protocol):
    def encode(self, text: str) -> list[float]:
        raise NotImplementedError


class VectorStorePort(Protocol):
    async def buscar_vacantes_similares(
        self, candidato_id: UUID, limite: int = 10, umbral: float = 0.5
    ) -> list[Recomendacion]:
        raise NotImplementedError
