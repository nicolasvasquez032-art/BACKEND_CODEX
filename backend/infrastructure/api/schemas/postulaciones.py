from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from domain.entities.postulacion import PostulacionEstado


class PostularseRequest(BaseModel):
    candidato_id: UUID   # ID de perfiles_candidato del candidato autenticado
    vacante_id: UUID


class CambiarEstadoPostulacionRequest(BaseModel):
    estado: PostulacionEstado


class PostulacionResponse(BaseModel):
    id: UUID
    candidato_id: UUID
    vacante_id: UUID
    estado: PostulacionEstado
    fecha: datetime
    score_match: float | None
