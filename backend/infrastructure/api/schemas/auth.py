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


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    role: UserRole
    created_at: datetime


class CandidateRegisterResponse(BaseModel):
    id: UUID
    user_id: UUID
    full_name: str
    skills: list[str]
    experience_years: int
    location: str | None
    education: str | None

