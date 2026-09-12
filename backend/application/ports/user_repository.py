from typing import Protocol
from uuid import UUID

from domain.entities.candidate_profile import CandidateProfile
from domain.entities.user import User, UserRole


class UserRepositoryPort(Protocol):
    async def find_by_email(self, email: str) -> User | None:
        raise NotImplementedError

    async def find_by_id(self, user_id: UUID) -> User | None:
        raise NotImplementedError

    async def create_user(self, email: str, password_hash: str, role: UserRole) -> User:
        raise NotImplementedError

    async def create_candidate_profile(
        self,
        user_id: UUID,
        full_name: str,
        skills: list[str],
        experience_years: int,
        location: str | None,
        education: str | None,
    ) -> CandidateProfile:
        raise NotImplementedError

    async def get_candidate_profile_by_user_id(self, user_id: UUID) -> CandidateProfile | None:
        raise NotImplementedError

