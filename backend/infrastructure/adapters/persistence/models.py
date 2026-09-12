from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from domain.entities.user import UserRole
from infrastructure.adapters.persistence.database import Base


class UserModel(Base):
    __tablename__ = "usuarios"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    candidate_profile: Mapped["CandidateProfileModel | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class CandidateProfileModel(Base):
    __tablename__ = "perfiles_candidato"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False, unique=True, index=True
    )
    full_name: Mapped[str] = mapped_column(String(180), nullable=False)
    skills: Mapped[list[str]] = mapped_column(ARRAY(String(80)), nullable=False, default=list)
    experience_years: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    location: Mapped[str | None] = mapped_column(String(180))
    education: Mapped[str | None] = mapped_column(String(180))
    cv_text: Mapped[str | None] = mapped_column(Text)

    user: Mapped[UserModel] = relationship(back_populates="candidate_profile")

