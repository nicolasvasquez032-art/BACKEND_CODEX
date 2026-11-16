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
    score_match: float | None = None
    candidato_nombre: str | None = None
    candidato_email: str | None = None
    candidato_job_title: str | None = None
    candidato_skills: list[str] | None = None
    candidato_experience_years: int | None = None
    candidato_location: str | None = None
    candidato_phone: str | None = None
    candidato_user_id: UUID | None = None
    vacante_titulo: str | None = None
    empresa_nombre: str | None = None
    vacante_ubicacion: str | None = None
    vacante_categoria: str | None = None
    vacante_salario_min: float | None = None
    vacante_salario_max: float | None = None
    vacante_descripcion: str | None = None
    vacante_requisitos: list[str] | None = None
