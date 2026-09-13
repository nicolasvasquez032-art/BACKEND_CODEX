from dataclasses import dataclass
from uuid import UUID

from application.ports.vacante_repository import VacanteRepositoryPort
from application.ports.ml_service_port import MlServicePort
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

    def __init__(self, vacantes: VacanteRepositoryPort, ml_service: MlServicePort) -> None:
        self._vacantes = vacantes
        self._ml_service = ml_service

    async def execute(self, command: PublicarVacanteCommand) -> Vacante:
        # 1. Crear vacante en BD
        vacante = await self._vacantes.create(
            empresa_id=command.empresa_id,
            titulo=command.titulo,
            descripcion=command.descripcion,
            requisitos=command.requisitos,
            ubicacion=command.ubicacion,
            categoria=command.categoria,
            salario_min=command.salario_min,
            salario_max=command.salario_max,
        )
        
        # 2. Generar embedding en background o asincronamente
        # Para evitar bloquear si falla, lo manejamos con cuidado
        try:
            texto_para_embedding = f"{vacante.titulo} {vacante.descripcion} {' '.join(vacante.requisitos)}"
            vector = await self._ml_service.get_vacante_embedding(texto_para_embedding)
            await self._vacantes.update_embedding(vacante.id, vector)
        except Exception as e:
            # En producción, esto debería ir a un log o encolarse para reintento
            print(f"Error generando embedding para vacante {vacante.id}: {e}")

        return vacante
