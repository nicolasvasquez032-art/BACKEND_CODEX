from dataclasses import dataclass

from application.ports.password_hasher import PasswordHasherPort
from application.ports.user_repository import UserRepositoryPort
from domain.entities.user import User, UserRole
from domain.exceptions import EmailAlreadyRegisteredError


@dataclass(frozen=True)
class RegisterCompanyCommand:
    email: str
    password: str


class RegisterCompanyUseCase:
    def __init__(self, users: UserRepositoryPort, password_hasher: PasswordHasherPort) -> None:
        self._users = users
        self._password_hasher = password_hasher

    async def execute(self, command: RegisterCompanyCommand) -> User:
        existing_user = await self._users.find_by_email(command.email)
        if existing_user is not None:
            raise EmailAlreadyRegisteredError("Email is already registered")

        return await self._users.create_user(
            email=command.email,
            password_hash=self._password_hasher.hash(command.password),
            role=UserRole.COMPANY,
        )

