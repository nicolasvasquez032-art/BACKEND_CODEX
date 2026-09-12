from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True)
class CandidateProfile:
    id: UUID
    user_id: UUID
    full_name: str
    skills: list[str] = field(default_factory=list)
    experience_years: int = 0
    location: str | None = None
    education: str | None = None
    cv_text: str | None = None

