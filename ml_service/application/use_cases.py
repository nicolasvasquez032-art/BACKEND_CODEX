from application.ports import EmbeddingModelPort
from domain.entities import TextEmbedding


class GenerateEmbeddingUseCase:
    def __init__(self, embedding_model: EmbeddingModelPort) -> None:
        self._embedding_model = embedding_model

    def execute(self, text: str) -> TextEmbedding:
        normalized_text = " ".join(text.split())
        return TextEmbedding(text=normalized_text, vector=self._embedding_model.encode(normalized_text))

