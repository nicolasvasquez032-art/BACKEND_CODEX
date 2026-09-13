from typing import Protocol
from uuid import UUID


class RecomendacionDTO:
    def __init__(
        self, vacante_id: UUID, titulo: str, empresa_id: UUID, score_similitud: float, explicacion: str
    ):
        self.vacante_id = vacante_id
        self.titulo = titulo
        self.empresa_id = empresa_id
        self.score_similitud = score_similitud
        self.explicacion = explicacion


class MlServicePort(Protocol):
    async def get_candidate_embedding(self, text: str) -> list[float]:
        raise NotImplementedError

    async def get_vacante_embedding(self, text: str) -> list[float]:
        raise NotImplementedError

    async def get_recomendaciones(self, candidato_id: UUID) -> list[RecomendacionDTO]:
        raise NotImplementedError
