"""Adaptador SMTP asíncrono que implementa EmailServicePort.

Usa aiosmtplib para envíos no bloqueantes. La configuración se lee
desde infrastructure.config (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM).
"""
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from infrastructure.config import settings


class SmtpEmailService:
    """Implementa EmailServicePort usando SMTP + aiosmtplib."""

    async def send_password_reset(self, to_email: str, reset_link: str) -> None:
        message = self._build_reset_message(to_email, reset_link)
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            use_tls=settings.smtp_use_tls,
        )

    @staticmethod
    def _build_reset_message(to_email: str, reset_link: str) -> MIMEMultipart:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "TalentMatch — Recuperación de contraseña"
        msg["From"] = settings.email_from
        msg["To"] = to_email

        text_body = (
            f"Hola,\n\n"
            f"Recibimos una solicitud para restablecer la contraseña de tu cuenta TalentMatch.\n\n"
            f"Haz clic en el siguiente enlace para crear una nueva contraseña (válido por 1 hora):\n"
            f"{reset_link}\n\n"
            f"Si no solicitaste este cambio, ignora este correo.\n\n"
            f"Equipo TalentMatch"
        )

        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: #4F46E5;">Recuperación de contraseña</h2>
            <p>Recibimos una solicitud para restablecer la contraseña de tu cuenta TalentMatch.</p>
            <p>
              <a href="{reset_link}"
                 style="background:#4F46E5;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;">
                Restablecer contraseña
              </a>
            </p>
            <p style="color:#888;font-size:12px;">
              Este enlace es válido por <strong>1 hora</strong>.<br>
              Si no solicitaste este cambio, ignora este correo.
            </p>
          </body>
        </html>
        """

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))
        return msg
