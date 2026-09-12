class DomainError(Exception):
    """Base exception for domain and application errors."""


class EmailAlreadyRegisteredError(DomainError):
    pass


class InvalidCredentialsError(DomainError):
    pass


class PermissionDeniedError(DomainError):
    pass

