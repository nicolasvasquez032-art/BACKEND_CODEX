from functools import lru_cache
from typing import Any

from infrastructure.config import settings


class SentenceTransformersEmbeddingModel:
    def __init__(self, model: Any = None) -> None:
        if model is not None:
            self._model = model
            self._is_fastembed = False
        else:
            try:
                from fastembed import TextEmbedding
                self._model = TextEmbedding(model_name=settings.embedding_model_name)
                self._is_fastembed = True
            except Exception:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(settings.embedding_model_name)
                self._is_fastembed = False

    def encode(self, text: str) -> list[float]:
        if self._is_fastembed:
            vectors = list(self._model.embed([text]))
            return vectors[0].tolist()
        return self._model.encode(text, normalize_embeddings=True).tolist()


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformersEmbeddingModel:
    return SentenceTransformersEmbeddingModel()


