from typing import Protocol


class EmbeddingModelPort(Protocol):
    def encode(self, text: str) -> list[float]:
        raise NotImplementedError

