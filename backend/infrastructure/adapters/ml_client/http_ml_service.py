import httpx
from uuid import UUID

from application.ports.ml_service_port import MlServicePort, RecomendacionDTO


class HttpMlServiceAdapter(MlServicePort):
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    async def _post_text(self, endpoint: str, text: str) -> list[float]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url}/ml/embedding/{endpoint}",
                json={"text": text},
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()["vector"]

    async def get_candidate_embedding(self, text: str) -> list[float]:
        return await self._post_text("candidato", text)

    async def get_vacante_embedding(self, text: str) -> list[float]:
        return await self._post_text("vacante", text)

    async def get_recomendaciones(self, candidato_id: UUID) -> list[RecomendacionDTO]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url}/ml/recomendaciones",
                json={"candidato_id": str(candidato_id)},
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            return [
                RecomendacionDTO(
                    vacante_id=UUID(r["vacante_id"]),
                    titulo=r["titulo"],
                    empresa_id=UUID(r["empresa_id"]),
                    score_similitud=r["score_similitud"],
                    explicacion=r["explicacion"]
                )
                for r in data
            ]
