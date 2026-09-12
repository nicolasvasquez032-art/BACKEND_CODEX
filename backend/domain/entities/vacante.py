from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class VacanteEstado(StrEnum):
    ACTIVA = "activa"
    PAUSADA = "pausada"
    CERRADA = "cerrada"


@dataclass(frozen=True)
class Vacante:
    """Entidad de dominio que representa una oferta de trabajo.

    El embedding se almacena como lista de floats; se genera en el
    microservicio ML (Sprint 3) y se guarda aquí para búsquedas de similitud.
    """

    id: UUID
    empresa_id: UUID          # FK al usuario empresa
    titulo: str
    descripcion: str
    requisitos: list[str]
    ubicacion: str
    estado: VacanteEstado
    creado_en: datetime
    salario_min: float | None = None
    salario_max: float | None = None
    categoria: str | None = None
    # El embedding se rellena en Sprint 3; None hasta entonces
    embedding: list[float] | None = field(default=None, compare=False, hash=False)

    def esta_activa(self) -> bool:
        return self.estado == VacanteEstado.ACTIVA

    def puede_ser_editada_por(self, usuario_id: UUID) -> bool:
        """Solo la empresa dueña puede editar la vacante."""
        return self.empresa_id == usuario_id
