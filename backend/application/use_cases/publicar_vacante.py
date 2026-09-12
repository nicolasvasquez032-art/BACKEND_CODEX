from dataclasses import dataclass
from uuid import UUID

from application.ports.vacante_repository import VacanteRepositoryPort
from domain.entities.vacante import Vacante


@dataclass(frozen=True)
class PublicarVacanteCommand:
    empresa_id: UUID
    titulo: str
    descripcion: str
    requisitos: list[str]
    ubicacion: str
    categoria: str | None = None
    salario_min: float | None = None
    salario_max: float | None = None


class PublicarVacanteUseCase:
    """Publica una nueva vacante. Solo usuarios con rol 'empresa' deben invocar este caso de uso.

    La validación de rol ocurre en el adaptador de entrada (router FastAPI).
    Este caso de uso solo orquesta la persistencia.
    """

    def __init__(self, vacantes: VacanteRepositoryPort) -> None:
        self._vacantes = vacantes

    async def execute(self, command: PublicarVacanteCommand) -> Vacante:
        return await self._vacantes.create(
            empresa_id=command.empresa_id,
            titulo=command.titulo,
            descripcion=command.descripcion,
            requisitos=command.requisitos,
            ubicacion=command.ubicacion,
            categoria=command.categoria,
            salario_min=command.salario_min,
            salario_max=command.salario_max,
        )
