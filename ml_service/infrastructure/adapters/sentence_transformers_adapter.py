from functools import lru_cache

from sentence_transformers import SentenceTransformer

from infrastructure.config import settings


class SentenceTransformersEmbeddingModel:
    def __init__(self, model: SentenceTransformer) -> None:
        self._model = model

    def encode(self, text: str) -> list[float]:
        return self._model.encode(text, normalize_embeddings=True).tolist()


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformersEmbeddingModel:
    return SentenceTransformersEmbeddingModel(SentenceTransformer(settings.embedding_model_name))

