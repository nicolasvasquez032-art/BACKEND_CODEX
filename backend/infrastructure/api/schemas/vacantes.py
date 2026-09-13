from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from domain.entities.vacante import VacanteEstado


class PublicarVacanteRequest(BaseModel):
    titulo: str = Field(min_length=3, max_length=200)
    descripcion: str = Field(min_length=10)
    requisitos: list[str] = Field(default_factory=list)
    ubicacion: str = Field(min_length=2, max_length=180)
    categoria: str | None = Field(default=None, max_length=100)
    salario_min: float | None = Field(default=None, ge=0)
    salario_max: float | None = Field(default=None, ge=0)
    latitud: float | None = None
    longitud: float | None = None


class ActualizarVacanteRequest(BaseModel):
    titulo: str = Field(min_length=3, max_length=200)
    descripcion: str = Field(min_length=10)
    requisitos: list[str] = Field(default_factory=list)
    ubicacion: str = Field(min_length=2, max_length=180)
    categoria: str | None = Field(default=None, max_length=100)
    salario_min: float | None = Field(default=None, ge=0)
    salario_max: float | None = Field(default=None, ge=0)
    latitud: float | None = None
    longitud: float | None = None


class CambiarEstadoVacanteRequest(BaseModel):
    estado: VacanteEstado


class VacanteResponse(BaseModel):
    id: UUID
    empresa_id: UUID
    titulo: str
    descripcion: str
    requisitos: list[str]
    ubicacion: str
    estado: VacanteEstado
    categoria: str | None
    salario_min: float | None
    salario_max: float | None
    latitud: float | None = None
    longitud: float | None = None
    creado_en: datetime
