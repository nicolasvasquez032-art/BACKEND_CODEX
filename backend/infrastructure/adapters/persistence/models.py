from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from domain.entities.postulacion import PostulacionEstado
from domain.entities.user import UserRole
from domain.entities.vacante import VacanteEstado
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
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384))

    user: Mapped[UserModel] = relationship(back_populates="candidate_profile")


class PasswordResetTokenModel(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    user: Mapped[UserModel] = relationship()


class VacanteModel(Base):
    __tablename__ = "vacantes"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    empresa_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False, index=True
    )
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    requisitos: Mapped[list[str]] = mapped_column(ARRAY(String(100)), nullable=False, default=list)
    ubicacion: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    estado: Mapped[VacanteEstado] = mapped_column(
        Enum(VacanteEstado, name="vacante_estado"),
        nullable=False,
        default=VacanteEstado.ACTIVA,
    )
    categoria: Mapped[str | None] = mapped_column(String(100), index=True)
    salario_min: Mapped[float | None] = mapped_column(Float)
    salario_max: Mapped[float | None] = mapped_column(Float)
    latitud: Mapped[float | None] = mapped_column(Float)
    longitud: Mapped[float | None] = mapped_column(Float)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384))

    empresa: Mapped[UserModel] = relationship()
    postulaciones: Mapped[list["PostulacionModel"]] = relationship(
        back_populates="vacante", cascade="all, delete-orphan"
    )


class PostulacionModel(Base):
    __tablename__ = "postulaciones"
    __table_args__ = (
        UniqueConstraint("candidato_id", "vacante_id", name="uq_candidato_vacante"),
    )

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    candidato_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("perfiles_candidato.id"),
        nullable=False,
        index=True,
    )
    vacante_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vacantes.id"), nullable=False, index=True
    )
    estado: Mapped[PostulacionEstado] = mapped_column(
        Enum(PostulacionEstado, name="postulacion_estado"),
        nullable=False,
        default=PostulacionEstado.POSTULADO,
    )
    score_match: Mapped[float | None] = mapped_column(Float)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    vacante: Mapped[VacanteModel] = relationship(back_populates="postulaciones")
    candidato: Mapped[CandidateProfileModel] = relationship()


class NotificacionModel(Base):
    __tablename__ = "notificaciones"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    usuario_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    leido: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    
    usuario: Mapped[UserModel] = relationship()


class DeviceTokenModel(Base):
    __tablename__ = "device_tokens"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    usuario_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False, index=True
    )
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    dispositivo_info: Mapped[str | None] = mapped_column(String(255))
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    usuario: Mapped[UserModel] = relationship()
