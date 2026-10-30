from dataclasses import dataclass
import logging
from uuid import UUID

logger = logging.getLogger(__name__)

from application.ports.cv_parser import CvParserPort
from application.ports.file_storage_port import FileStoragePort
from application.ports.ml_service_port import MlServicePort
from application.ports.user_repository import UserRepositoryPort
from domain.entities.candidate_profile import CandidateProfile
from domain.exceptions import CVProcessingError, PermissionDeniedError, ProfileNotFoundError

_SUPPORTED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}
_MAX_CV_BYTES = 10 * 1024 * 1024  # 10 MB


@dataclass(frozen=True)
class UploadCvCommand:
    profile_id: UUID
    requesting_user_id: UUID   # ID del usuario autenticado
    file_bytes: bytes
    mime_type: str
    file_name: str = "curriculum.pdf"


class UploadCvUseCase:
    """Procesa la carga de un CV (PDF o imagen), persiste el archivo original en S3 y extrae su texto."""

    def __init__(
        self,
        users: UserRepositoryPort,
        cv_parser: CvParserPort,
        ml_service: MlServicePort,
        storage: FileStoragePort | None = None,
    ) -> None:
        self._users = users
        self._cv_parser = cv_parser
        self._ml_service = ml_service
        self._storage = storage

    async def execute(self, command: UploadCvCommand) -> CandidateProfile:
        profile = await self._users.get_candidate_profile_by_id(command.profile_id)
        if profile is None:
            raise ProfileNotFoundError(f"Perfil {command.profile_id} no encontrado")

        if profile.user_id != command.requesting_user_id:
            raise PermissionDeniedError("Solo el candidato dueño puede subir su CV")

        if command.mime_type not in _SUPPORTED_MIME_TYPES:
            raise CVProcessingError(
                f"Tipo de archivo no soportado: {command.mime_type}. "
                f"Use PDF, JPG, PNG o WEBP."
            )

        if len(command.file_bytes) > _MAX_CV_BYTES:
            raise CVProcessingError("El archivo no puede superar los 10 MB")

        cv_text = self._cv_parser.extract_text(command.file_bytes, command.mime_type)

        if not cv_text.strip():
            raise CVProcessingError(
                "No se pudo extraer texto del archivo. "
                "Asegúrese de que el PDF no sea una imagen escaneada sin OCR, "
                "o suba directamente la imagen del documento."
            )

        file_key: str | None = None
        if self._storage:
            try:
                file_key = await self._storage.upload_file(
                    command.file_bytes, command.file_name, command.mime_type
                )
            except Exception as e:
                logger.error(f"Error subiendo archivo original de CV a storage: {e}")

        updated_profile = await self._users.update_cv_text(
            profile_id=command.profile_id,
            cv_text=cv_text,
            cv_file_url=file_key,
        )

        try:
            texto_para_embedding = f"{updated_profile.full_name} {' '.join(updated_profile.skills)} {updated_profile.education or ''} {updated_profile.cv_text or ''}"
            if hasattr(self._ml_service, "schedule_embedding_update"):
                self._ml_service.schedule_embedding_update(updated_profile.id, texto_para_embedding)
            else:
                vector = await self._ml_service.get_candidate_embedding(texto_para_embedding)
                await self._users.update_embedding_candidato(updated_profile.id, vector)
        except Exception as e:
            logger.error(f"Error generando embedding para perfil {updated_profile.id}: {e}")

        return updated_profile
