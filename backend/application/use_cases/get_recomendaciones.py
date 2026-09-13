from uuid import UUID

from application.ports.ml_service_port import MlServicePort, RecomendacionDTO


class GetRecomendacionesUseCase:
    def __init__(self, ml_service: MlServicePort) -> None:
        self._ml_service = ml_service

    async def execute(self, candidato_id: UUID) -> list[RecomendacionDTO]:
        return await self._ml_service.get_recomendaciones(candidato_id)
