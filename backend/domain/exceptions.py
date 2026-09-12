class DomainError(Exception):
    """Base exception for domain and application errors."""


class EmailAlreadyRegisteredError(DomainError):
    pass


class InvalidCredentialsError(DomainError):
    pass


class PermissionDeniedError(DomainError):
    pass


class UserNotFoundError(DomainError):
    pass


class ProfileNotFoundError(DomainError):
    pass


class CVProcessingError(DomainError):
    pass


class InvalidResetTokenError(DomainError):
    pass


class VacanteNotFoundError(DomainError):
    pass


class PostulacionNotFoundError(DomainError):
    pass


class DuplicatePostulacionError(DomainError):
    pass


class InvalidEstadoTransitionError(DomainError):
    pass

