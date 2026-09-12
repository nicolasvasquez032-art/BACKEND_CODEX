from dataclasses import dataclass
from uuid import UUID

from application.ports.cv_parser import CvParserPort
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


class UploadCvUseCase:
    """Procesa la carga de un CV (PDF o imagen) y persiste el texto extraído.

    Flujo:
    1. Valida que el usuario sea dueño del perfil.
    2. Valida el mime type y el tamaño del archivo.
    3. Delega la extracción de texto al CvParserPort.
    4. Guarda el texto en el perfil.
    """

    def __init__(self, users: UserRepositoryPort, cv_parser: CvParserPort) -> None:
        self._users = users
        self._cv_parser = cv_parser

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

        return await self._users.update_cv_text(
            profile_id=command.profile_id,
            cv_text=cv_text,
        )
