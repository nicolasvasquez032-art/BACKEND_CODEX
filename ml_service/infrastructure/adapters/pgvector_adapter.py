from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from application.ports import VectorStorePort
from domain.entities import Recomendacion


class PgVectorAdapter(VectorStorePort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def buscar_vacantes_similares(
        self, candidato_id: UUID, limite: int = 10, umbral: float = 0.5
    ) -> list[Recomendacion]:
        # Usamos 1 - distancia_coseno (<=>) para obtener la similitud
        query = text(
            """
            SELECT 
                v.id as vacante_id,
                v.titulo,
                v.empresa_id,
                1 - (v.embedding <=> p.embedding) as score_similitud
            FROM vacantes v
            JOIN perfiles_candidato p ON p.id = :candidato_id
            WHERE v.estado = 'ACTIVA' 
              AND v.embedding IS NOT NULL 
              AND p.embedding IS NOT NULL
              AND 1 - (v.embedding <=> p.embedding) >= :umbral
            ORDER BY score_similitud DESC
            LIMIT :limite;
            """
        )
        
        result = await self._session.execute(
            query, 
            {
                "candidato_id": candidato_id, 
                "umbral": umbral, 
                "limite": limite
            }
        )
        
        recomendaciones = []
        for row in result.mappings():
            recomendaciones.append(
                Recomendacion(
                    vacante_id=row["vacante_id"],
                    titulo=row["titulo"],
                    empresa_id=row["empresa_id"],
                    score_similitud=row["score_similitud"],
                    explicacion="Recomendado por alta similitud semántica con tu perfil."
                )
            )
            
        return recomendaciones
