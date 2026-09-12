from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgresql+asyncpg://talentmatch:talentmatch@localhost:5432/talentmatch"
    )
    jwt_secret_key: str = Field(default="change-me-in-development")
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=60)
    ml_service_url: str = Field(default="http://localhost:8001")

    # SMTP / Email
    smtp_host: str = Field(default="localhost")
    smtp_port: int = Field(default=1025)
    smtp_user: str = Field(default="")
    smtp_password: str = Field(default="")
    smtp_use_tls: bool = Field(default=False)
    email_from: str = Field(default="noreply@talentmatch.app")

    # URL base del frontend (para enlaces de reset de contraseña)
    frontend_url: str = Field(default="http://localhost:3000")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

