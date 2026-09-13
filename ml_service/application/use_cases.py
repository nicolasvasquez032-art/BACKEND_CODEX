from uuid import UUID

from application.ports import EmbeddingModelPort, VectorStorePort
from domain.entities import Recomendacion, TextEmbedding


class GenerateEmbeddingUseCase:
    def __init__(self, embedding_model: EmbeddingModelPort) -> None:
        self._embedding_model = embedding_model

    def execute(self, text: str) -> TextEmbedding:
        normalized_text = " ".join(text.split())
        vector = self._embedding_model.encode(normalized_text)
        return TextEmbedding(text=normalized_text, vector=vector)


class GenerarRecomendacionesUseCase:
    def __init__(self, vector_store: VectorStorePort) -> None:
        self._vector_store = vector_store

    async def execute(
        self, candidato_id: UUID, limite: int = 10, umbral: float = 0.5
    ) -> list[Recomendacion]:
        # Aquí se podría incluir lógica adicional como pre-filtros duros o post-procesamiento.
        # Por ahora delegamos al puerto que se encarga del cruce vectorial.
        recomendaciones = await self._vector_store.buscar_vacantes_similares(
            candidato_id, limite, umbral
        )
        return recomendaciones
