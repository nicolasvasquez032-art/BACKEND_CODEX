from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from domain.entities.postulacion import PostulacionEstado


class PostularseRequest(BaseModel):
    vacante_id: UUID   # candidato_id se extrae del JWT automáticamente


class CambiarEstadoPostulacionRequest(BaseModel):
    estado: PostulacionEstado


class PostulacionResponse(BaseModel):
    id: UUID
    candidato_id: UUID
    vacante_id: UUID
    estado: PostulacionEstado
    fecha: datetime
    score_match: float | None
