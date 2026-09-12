from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.candidate_profile import CandidateProfile
from domain.entities.password_reset_token import PasswordResetToken
from domain.entities.user import User, UserRole
from infrastructure.adapters.persistence.models import (
    CandidateProfileModel,
    PasswordResetTokenModel,
    UserModel,
)


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Usuarios ────────────────────────────────────────────────────────────

    async def find_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(UserModel).where(UserModel.email == email))
        model = result.scalar_one_or_none()
        return self._to_user_entity(model) if model else None

    async def find_by_id(self, user_id: UUID) -> User | None:
        model = await self._session.get(UserModel, user_id)
        return self._to_user_entity(model) if model else None

    async def create_user(self, email: str, password_hash: str, role: UserRole) -> User:
        model = UserModel(email=email, password_hash=password_hash, role=role)
        self._session.add(model)
        await self._session.flush()
        return self._to_user_entity(model)

    async def update_user_password(self, user_id: UUID, new_password_hash: str) -> None:
        model = await self._session.get(UserModel, user_id)
        if model is not None:
            model.password_hash = new_password_hash
            await self._session.flush()

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
        model = CandidateProfileModel(
            user_id=user_id,
            full_name=full_name,
            skills=skills,
            experience_years=experience_years,
            location=location,
            education=education,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_candidate_profile_entity(model)

    async def get_candidate_profile_by_user_id(self, user_id: UUID) -> CandidateProfile | None:
        result = await self._session.execute(
            select(CandidateProfileModel).where(CandidateProfileModel.user_id == user_id)
        )
        model = result.scalar_one_or_none()
        return self._to_candidate_profile_entity(model) if model else None

    async def get_candidate_profile_by_id(self, profile_id: UUID) -> CandidateProfile | None:
        model = await self._session.get(CandidateProfileModel, profile_id)
        return self._to_candidate_profile_entity(model) if model else None

    async def update_candidate_profile(
        self,
        profile_id: UUID,
        full_name: str,
        skills: list[str],
        experience_years: int,
        location: str | None,
        education: str | None,
    ) -> CandidateProfile:
        model = await self._session.get(CandidateProfileModel, profile_id)
        if model is None:
            raise ValueError(f"Perfil {profile_id} no encontrado en BD")
        model.full_name = full_name
        model.skills = skills
        model.experience_years = experience_years
        model.location = location
        model.education = education
        await self._session.flush()
        return self._to_candidate_profile_entity(model)

    async def update_cv_text(self, profile_id: UUID, cv_text: str) -> CandidateProfile:
        model = await self._session.get(CandidateProfileModel, profile_id)
        if model is None:
            raise ValueError(f"Perfil {profile_id} no encontrado en BD")
        model.cv_text = cv_text
        await self._session.flush()
        return self._to_candidate_profile_entity(model)

    # ── Tokens de recuperación de contraseña ────────────────────────────────

    async def create_password_reset_token(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> PasswordResetToken:
        model = PasswordResetTokenModel(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_reset_token_entity(model)

    async def find_password_reset_token(self, token_hash: str) -> PasswordResetToken | None:
        result = await self._session.execute(
            select(PasswordResetTokenModel).where(
                PasswordResetTokenModel.token_hash == token_hash
            )
        )
        model = result.scalar_one_or_none()
        return self._to_reset_token_entity(model) if model else None

    async def mark_token_used(self, token_id: UUID) -> None:
        model = await self._session.get(PasswordResetTokenModel, token_id)
        if model is not None:
            model.used = True
            await self._session.flush()

    # ── Mapeadores a entidades de dominio ───────────────────────────────────

    @staticmethod
    def _to_user_entity(model: UserModel) -> User:
        return User(
            id=model.id,
            email=model.email,
            password_hash=model.password_hash,
            role=model.role,
            created_at=model.created_at,
        )

    @staticmethod
    def _to_candidate_profile_entity(model: CandidateProfileModel) -> CandidateProfile:
        return CandidateProfile(
            id=model.id,
            user_id=model.user_id,
            full_name=model.full_name,
            skills=list(model.skills),
            experience_years=model.experience_years,
            location=model.location,
            education=model.education,
            cv_text=model.cv_text,
        )

    @staticmethod
    def _to_reset_token_entity(model: PasswordResetTokenModel) -> PasswordResetToken:
        return PasswordResetToken(
            id=model.id,
            user_id=model.user_id,
            token_hash=model.token_hash,
            expires_at=model.expires_at,
            used=model.used,
        )
