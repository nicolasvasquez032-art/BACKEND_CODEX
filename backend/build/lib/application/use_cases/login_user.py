from dataclasses import dataclass

from application.ports.password_hasher import PasswordHasherPort
from application.ports.token_service import TokenServicePort
from application.ports.user_repository import UserRepositoryPort
from domain.exceptions import InvalidCredentialsError


@dataclass(frozen=True)
class LoginUserCommand:
    email: str
    password: str


@dataclass(frozen=True)
class LoginResult:
    access_token: str
    token_type: str = "bearer"


class LoginUserUseCase:
    def __init__(
        self,
        users: UserRepositoryPort,
        password_hasher: PasswordHasherPort,
        token_service: TokenServicePort,
    ) -> None:
        self._users = users
        self._password_hasher = password_hasher
        self._token_service = token_service

    async def execute(self, command: LoginUserCommand) -> LoginResult:
        user = await self._users.find_by_email(command.email)
        if user is None or not self._password_hasher.verify(command.password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password")

        return LoginResult(access_token=self._token_service.create_access_token(user))

