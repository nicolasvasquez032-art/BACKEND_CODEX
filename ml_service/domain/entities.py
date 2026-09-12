from dataclasses import dataclass


@dataclass(frozen=True)
class TextEmbedding:
    text: str
    vector: list[float]

