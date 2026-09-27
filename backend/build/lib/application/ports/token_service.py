from typing import Protocol

from domain.entities.user import User


class TokenServicePort(Protocol):
    def create_access_token(self, user: User) -> str:
        raise NotImplementedError

