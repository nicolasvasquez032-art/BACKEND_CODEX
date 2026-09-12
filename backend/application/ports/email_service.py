from typing import Protocol


class EmailServicePort(Protocol):
    """Puerto para el envío de correos electrónicos."""

    async def send_password_reset(self, to_email: str, reset_link: str) -> None:
        """Envía un correo con el enlace de recuperación de contraseña."""
        raise NotImplementedError
