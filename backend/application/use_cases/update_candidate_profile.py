from dataclasses import dataclass
from uuid import UUID

from application.ports.user_repository import UserRepositoryPort
from domain.entities.candidate_profile import CandidateProfile
from domain.exceptions import PermissionDeniedError, ProfileNotFoundError


@dataclass(frozen=True)
class UpdateCandidateProfileCommand:
    profile_id: UUID
    requesting_user_id: UUID        # ID del usuario autenticado
    full_name: str
    skills: list[str]
    experience_years: int
    location: str | None = None
    education: str | None = None


class UpdateCandidateProfileUseCase:
    """Actualiza los datos de perfil de un candidato.

    Solo el propio candidato puede editar su perfil.
    """

    def __init__(self, users: UserRepositoryPort) -> None:
        self._users = users

    async def execute(self, command: UpdateCandidateProfileCommand) -> CandidateProfile:
        profile = await self._users.get_candidate_profile_by_id(command.profile_id)
        if profile is None:
            raise ProfileNotFoundError(f"Perfil {command.profile_id} no encontrado")

        if profile.user_id != command.requesting_user_id:
            raise PermissionDeniedError("Solo el candidato dueño puede editar su perfil")

        return await self._users.update_candidate_profile(
            profile_id=command.profile_id,
            full_name=command.full_name,
            skills=command.skills,
            experience_years=command.experience_years,
            location=command.location,
            education=command.education,
        )
