from dataclasses import dataclass
from uuid import UUID

from application.ports.user_repository import UserRepositoryPort
from domain.entities.candidate_profile import CandidateProfile
from domain.exceptions import PermissionDeniedError, ProfileNotFoundError


@dataclass(frozen=True)
class GetCandidateProfileCommand:
    profile_id: UUID
    requesting_user_id: UUID
    requesting_user_role: str   # 'candidate' | 'company' | 'admin'


class GetCandidateProfileUseCase:
    """Recupera el perfil de un candidato.

    Reglas de acceso:
    - El propio candidato puede ver su perfil siempre.
    - Empresas y administradores también pueden verlo.
    - Un candidato NO puede ver el perfil de otro candidato.
    """

    def __init__(self, users: UserRepositoryPort) -> None:
        self._users = users

    async def execute(self, command: GetCandidateProfileCommand) -> CandidateProfile:
        profile = await self._users.get_candidate_profile_by_id(command.profile_id)
        if profile is None:
            raise ProfileNotFoundError(f"Perfil {command.profile_id} no encontrado")

        if command.requesting_user_role == "candidate":
            # El candidato solo puede ver su propio perfil
            if profile.user_id != command.requesting_user_id:
                raise PermissionDeniedError("No tienes permiso para ver este perfil")

        return profile
