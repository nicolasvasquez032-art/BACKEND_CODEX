from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class PostulacionEstado(StrEnum):
    POSTULADO = "postulado"
    ENTREVISTA = "entrevista"
    RECHAZADO = "rechazado"
    CONTRATADO = "contratado"


@dataclass(frozen=True)
class Postulacion:
    """Entidad de dominio que representa la postulación de un candidato a una vacante.

    La unicidad (candidato_id, vacante_id) se garantiza tanto en BD (restricción)
    como en la regla de negocio del dominio (RF-03.2).
    """

    id: UUID
    candidato_id: UUID        # FK a perfiles_candidato
    vacante_id: UUID          # FK a vacantes
    estado: PostulacionEstado
    fecha: datetime
    score_match: float | None = None   # Llenado por el motor ML en Sprint 3

    def puede_cambiar_estado(self, nuevo_estado: PostulacionEstado) -> bool:
        """Valida transiciones de estado permitidas (flujo kanban de empresa).

        Transiciones válidas:
          postulado → entrevista | rechazado
          entrevista → contratado | rechazado
          rechazado / contratado → estado final (no se puede cambiar)
        """
        transiciones = {
            PostulacionEstado.POSTULADO: {
                PostulacionEstado.ENTREVISTA,
                PostulacionEstado.RECHAZADO,
            },
            PostulacionEstado.ENTREVISTA: {
                PostulacionEstado.CONTRATADO,
                PostulacionEstado.RECHAZADO,
            },
        }
        return nuevo_estado in transiciones.get(self.estado, set())
