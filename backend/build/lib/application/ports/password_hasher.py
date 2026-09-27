from typing import Protocol


class PasswordHasherPort(Protocol):
    def hash(self, password: str) -> str:
        raise NotImplementedError

    def verify(self, plain_password: str, password_hash: str) -> bool:
        raise NotImplementedError

