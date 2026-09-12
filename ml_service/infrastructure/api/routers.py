from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from application.use_cases import GenerateEmbeddingUseCase
from infrastructure.adapters.sentence_transformers_adapter import (
    SentenceTransformersEmbeddingModel,
    get_embedding_model,
)

health_router = APIRouter(tags=["health"])
embedding_router = APIRouter(prefix="/ml", tags=["embeddings"])


class EmbeddingRequest(BaseModel):
    text: str = Field(min_length=1)


class EmbeddingResponse(BaseModel):
    vector: list[float]
    dimensions: int


@health_router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@embedding_router.post("/embedding/candidato", response_model=EmbeddingResponse)
async def create_candidate_embedding(
    request: EmbeddingRequest,
    model: SentenceTransformersEmbeddingModel = Depends(get_embedding_model),
) -> EmbeddingResponse:
    result = GenerateEmbeddingUseCase(model).execute(request.text)
    return EmbeddingResponse(vector=result.vector, dimensions=len(result.vector))


@embedding_router.post("/embedding/vacante", response_model=EmbeddingResponse)
async def create_job_embedding(
    request: EmbeddingRequest,
    model: SentenceTransformersEmbeddingModel = Depends(get_embedding_model),
) -> EmbeddingResponse:
    result = GenerateEmbeddingUseCase(model).execute(request.text)
    return EmbeddingResponse(vector=result.vector, dimensions=len(result.vector))

