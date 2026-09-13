from dataclasses import dataclass
from uuid import UUID

from application.ports.vacante_repository import VacanteRepositoryPort
from application.ports.ml_service_port import MlServicePort
from application.ports.notificacion_ports import NotificacionRepositoryPort, PushNotificationPort
from domain.entities.vacante import Vacante
from domain.entities.notificacion import Notificacion


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
    latitud: float | None = None
    longitud: float | None = None


class PublicarVacanteUseCase:
    """Publica una nueva vacante. Solo usuarios con rol 'empresa' deben invocar este caso de uso."""

    def __init__(
        self,
        vacantes: VacanteRepositoryPort,
        ml_service: MlServicePort,
        notificacion_repo: NotificacionRepositoryPort,
        push_port: PushNotificationPort,
    ) -> None:
        self._vacantes = vacantes
        self._ml_service = ml_service
        self._notificacion_repo = notificacion_repo
        self._push_port = push_port

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
            latitud=command.latitud,
            longitud=command.longitud,
        )
        
        # 2. Generar embedding en background o asincronamente
        # Para evitar bloquear si falla, lo manejamos con cuidado
        try:
            texto_para_embedding = f"{vacante.titulo} {vacante.descripcion} {' '.join(vacante.requisitos)}"
            vector = await self._ml_service.get_vacante_embedding(texto_para_embedding)
            await self._vacantes.update_embedding(vacante.id, vector)
            
            # 3. Consultar candidatos compatibles y notificar
            match_candidatos = await self._ml_service.get_match_candidatos(vacante.id)
            for match in match_candidatos:
                # Guardar notificación en BD
                notificacion = Notificacion(
                    usuario_id=match.usuario_id,
                    tipo="NUEVA_VACANTE",
                    mensaje=f"¡Nueva vacante para ti! {vacante.titulo} hace match con tu perfil."
                )
                await self._notificacion_repo.save_notificacion(notificacion)
                
                # Enviar push notification si tiene token
                device_token = await self._notificacion_repo.get_device_token_by_usuario_id(match.usuario_id)
                if device_token:
                    await self._push_port.send_notification(
                        token=device_token.token,
                        title="Nueva vacante recomendada",
                        body=f"{vacante.titulo} es ideal para tu perfil.",
                        data={"vacante_id": str(vacante.id)}
                    )
        except Exception as e:
            # En producción, esto debería ir a un log o encolarse para reintento
            import traceback
            traceback.print_exc()
            print(f"Error generando embedding/notificando vacante {vacante.id}: {e}")

        return vacante
