from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from application.use_cases import GenerateEmbeddingUseCase, GenerarRecomendacionesUseCase
from infrastructure.adapters.sentence_transformers_adapter import (
    SentenceTransformersEmbeddingModel,
    get_embedding_model,
)
from infrastructure.adapters.database import get_session
from infrastructure.adapters.pgvector_adapter import PgVectorAdapter

health_router = APIRouter(tags=["health"])
embedding_router = APIRouter(prefix="/ml", tags=["embeddings"])


class EmbeddingRequest(BaseModel):
    text: str = Field(min_length=1)


class EmbeddingResponse(BaseModel):
    vector: list[float]
    dimensions: int


class RecomendacionesRequest(BaseModel):
    candidato_id: UUID
    limite: int = Field(default=10, ge=1, le=50)
    umbral: float = Field(default=0.5, ge=0.0, le=1.0)


class RecomendacionResponse(BaseModel):
    vacante_id: UUID
    titulo: str
    empresa_id: UUID
    score_similitud: float
    explicacion: str


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


@embedding_router.post("/recomendaciones", response_model=list[RecomendacionResponse])
async def get_recomendaciones(
    request: RecomendacionesRequest,
    session: AsyncSession = Depends(get_session),
) -> list[RecomendacionResponse]:
    adapter = PgVectorAdapter(session)
    use_case = GenerarRecomendacionesUseCase(adapter)
    
    try:
        recomendaciones = await use_case.execute(
            candidato_id=request.candidato_id,
            limite=request.limite,
            umbral=request.umbral
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

    return [
        RecomendacionResponse(
            vacante_id=r.vacante_id,
            titulo=r.titulo,
            empresa_id=r.empresa_id,
            score_similitud=r.score_similitud,
            explicacion=r.explicacion
        )
        for r in recomendaciones
    ]

