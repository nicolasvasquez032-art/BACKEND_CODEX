from passlib.context import CryptContext
import passlib.handlers.bcrypt

# Monkeypatch for passlib + bcrypt >= 4.0.0 bug
passlib.handlers.bcrypt.detect_wrap_bug = lambda *args, **kwargs: False


class PasslibPasswordHasher:
    def __init__(self) -> None:
        self._context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash(self, password: str) -> str:
        return self._context.hash(password)

    def verify(self, plain_password: str, password_hash: str) -> bool:
        return self._context.verify(plain_password, password_hash)

