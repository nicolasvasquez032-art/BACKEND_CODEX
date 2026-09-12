from uuid import UUID

from pydantic import BaseModel, Field


class ProfileUpdateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=180)
    skills: list[str] = Field(default_factory=list)
    experience_years: int = Field(ge=0, le=80)
    location: str | None = Field(default=None, max_length=180)
    education: str | None = Field(default=None, max_length=180)


class ProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    full_name: str
    skills: list[str]
    experience_years: int
    location: str | None
    education: str | None
    cv_text: str | None


class CVUploadResponse(BaseModel):
    profile_id: UUID
    message: str
    cv_preview: str  # Primeros 200 caracteres del texto extraído
