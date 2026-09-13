from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class TextEmbedding:
    text: str
    vector: list[float]


@dataclass(frozen=True)
class Recomendacion:
    vacante_id: UUID
    titulo: str
    empresa_id: UUID
    score_similitud: float
    explicacion: str


@dataclass(frozen=True)
class MatchCandidato:
    candidato_id: UUID
    usuario_id: UUID
    nombre: str
    score_similitud: float
    explicacion: str

