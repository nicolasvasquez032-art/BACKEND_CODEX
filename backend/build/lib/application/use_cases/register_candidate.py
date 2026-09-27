from dataclasses import dataclass

from application.ports.password_hasher import PasswordHasherPort
from application.ports.user_repository import UserRepositoryPort
from domain.entities.candidate_profile import CandidateProfile
from domain.entities.user import UserRole
from domain.exceptions import EmailAlreadyRegisteredError


@dataclass(frozen=True)
class RegisterCandidateCommand:
    email: str
    password: str
    full_name: str
    skills: list[str]
    experience_years: int
    location: str | None = None
    education: str | None = None


class RegisterCandidateUseCase:
    def __init__(self, users: UserRepositoryPort, password_hasher: PasswordHasherPort) -> None:
        self._users = users
        self._password_hasher = password_hasher

    async def execute(self, command: RegisterCandidateCommand) -> CandidateProfile:
        existing_user = await self._users.find_by_email(command.email)
        if existing_user is not None:
            raise EmailAlreadyRegisteredError("Email is already registered")

        user = await self._users.create_user(
            email=command.email,
            password_hash=self._password_hasher.hash(command.password),
            role=UserRole.CANDIDATE,
        )
        return await self._users.create_candidate_profile(
            user_id=user.id,
            full_name=command.full_name,
            skills=command.skills,
            experience_years=command.experience_years,
            location=command.location,
            education=command.education,
        )

