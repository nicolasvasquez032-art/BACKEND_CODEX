from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class UserRole(StrEnum):
    CANDIDATE = "candidate"
    COMPANY = "company"
    ADMIN = "admin"


@dataclass(frozen=True)
class User:
    id: UUID
    email: str
    password_hash: str
    role: UserRole
    created_at: datetime

