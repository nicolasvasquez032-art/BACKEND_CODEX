from typing import Protocol
from uuid import UUID

from domain.entities.candidate_profile import CandidateProfile
from domain.entities.password_reset_token import PasswordResetToken
from domain.entities.user import User, UserRole


class UserRepositoryPort(Protocol):
    # ── Usuarios ────────────────────────────────────────────────────────────

    async def find_by_email(self, email: str) -> User | None:
        raise NotImplementedError

    async def find_by_id(self, user_id: UUID) -> User | None:
        raise NotImplementedError

    async def create_user(self, email: str, password_hash: str, role: UserRole) -> User:
        raise NotImplementedError

    async def update_user_password(self, user_id: UUID, new_password_hash: str) -> None:
        raise NotImplementedError

    # ── Perfiles de candidato ────────────────────────────────────────────────

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

    async def get_candidate_profile_by_id(self, profile_id: UUID) -> CandidateProfile | None:
        raise NotImplementedError

    async def update_candidate_profile(
        self,
        profile_id: UUID,
        full_name: str,
        skills: list[str],
        experience_years: int,
        location: str | None,
        education: str | None,
    ) -> CandidateProfile:
        raise NotImplementedError

    async def update_cv_text(self, profile_id: UUID, cv_text: str) -> CandidateProfile:
        raise NotImplementedError

    async def update_embedding_candidato(self, profile_id: UUID, embedding: list[float]) -> None:
        raise NotImplementedError

    # --- Password Reset Tokens ---de recuperación de contraseña ────────────────────────────────

    async def create_password_reset_token(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: object,  # datetime
    ) -> PasswordResetToken:
        raise NotImplementedError

    async def find_password_reset_token(self, token_hash: str) -> PasswordResetToken | None:
        raise NotImplementedError

    async def mark_token_used(self, token_id: UUID) -> None:
        raise NotImplementedError

