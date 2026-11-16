from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from domain.entities.user import UserRole


class CandidateRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=180)
    skills: list[str] = Field(default_factory=list)
    experience_years: int = Field(ge=0, le=80)
    location: str | None = Field(default=None, max_length=180)
    education: str | None = Field(default=None, max_length=180)


class CompanyRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    nombre: str | None = Field(default=None, max_length=180)


class CompanyProfileUpdateRequest(BaseModel):
    nombre: str = Field(min_length=2, max_length=180)
    sector: str | None = Field(default=None, max_length=100)
    ubicacion: str | None = Field(default=None, max_length=180)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str | None = None
    is_new_user: bool = False
    profile_id: str | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    role: UserRole
    created_at: datetime
    nombre: str | None = None


class CandidateRegisterResponse(BaseModel):
    id: UUID
    user_id: UUID
    full_name: str
    skills: list[str]
    experience_years: int
    location: str | None
    education: str | None
    phone: str | None = None
    portfolio_url: str | None = None
    about_me: str | None = None
    job_title: str | None = None


class RequestPasswordResetRequest(BaseModel):
    email: EmailStr


class ConfirmPasswordResetRequest(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    new_password: str = Field(min_length=8, max_length=128)


class SocialLoginRequest(BaseModel):
    provider: str = Field(description="google, facebook, o linkedin")
    token: str = Field(default="", description="Token de acceso, id_token o código de autorización")
    email: EmailStr | None = Field(default=None, description="Correo electrónico verificado por el proveedor")
    full_name: str | None = Field(default=None, description="Nombre completo del usuario obtenido del proveedor")
    avatar_url: str | None = Field(default=None, description="Foto de perfil del proveedor")


class SocialConfigResponse(BaseModel):
    google_configured: bool
    facebook_configured: bool
    linkedin_configured: bool
    google_client_id: str | None = None
    facebook_app_id: str | None = None
    linkedin_client_id: str | None = None


