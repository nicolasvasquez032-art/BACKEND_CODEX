from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.candidate_profile import CandidateProfile
from domain.entities.user import User, UserRole
from infrastructure.adapters.persistence.models import CandidateProfileModel, UserModel


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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

