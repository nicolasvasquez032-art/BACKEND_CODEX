from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/talentmatch"
    )
    database_read_replica_url: str | None = Field(
        default=None,
        description="URL opcional de la réplica de solo lectura para separar escrituras de lecturas masivas."
    )
    use_pgbouncer: bool = Field(default=False)
    db_pool_size: int = Field(default=20)
    db_max_overflow: int = Field(default=30)
    db_pool_timeout: int = Field(default=30)
    jwt_secret_key: str = Field(default="change-me-in-development")
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=60)
    jwt_refresh_token_expire_days: int = Field(default=7)
    ml_service_url: str = Field(default="http://localhost:8001")
    
    # Security Configurations
    environment: str = Field(default="development")
    cors_origins: str = Field(default="*")

    # Distributed caching / PubSub / Rate limiting (Factores VI y VIII)
    redis_url: str | None = Field(default=None)

    # Firebase Credentials vía variable de entorno directa (Factor III)
    firebase_credentials_json: str | None = Field(default=None)

    # SMTP / Email
    smtp_host: str = Field(default="localhost")
    smtp_port: int = Field(default=1025)
    smtp_user: str = Field(default="")
    smtp_password: str = Field(default="")
    smtp_use_tls: bool = Field(default=False)
    email_from: str = Field(default="noreply@talentmatch.app")

    # URL base del frontend (para enlaces de reset de contraseña)
    frontend_url: str = Field(default="http://localhost:3000")
    api_base_url: str = Field(default="https://talentmatch-api.duckdns.org")

    # Mercado Pago
    mp_access_token: str = Field(default="")
    mp_webhook_secret: str = Field(default="")
    mp_back_url_base: str = Field(default="http://localhost:3000")

    # AWS S3 Storage para CVs
    aws_access_key_id: str | None = Field(default=None)
    aws_secret_access_key: str | None = Field(default=None)
    aws_region: str = Field(default="us-east-2")
    s3_bucket_name: str = Field(default="talentmatch-cvs")
    s3_presigned_url_expire_seconds: int = Field(default=900)

    # Sentry Error Monitoring & APM
    sentry_dsn: str | None = Field(default=None)
    sentry_environment: str = Field(default="development")
    sentry_traces_sample_rate: float = Field(default=1.0)

    # OAuth Social Providers (Google, Facebook, LinkedIn)
    google_client_id: str = Field(default="")
    google_client_secret: str = Field(default="")
    facebook_app_id: str = Field(default="")
    facebook_app_secret: str = Field(default="")
    linkedin_client_id: str = Field(default="")
    linkedin_client_secret: str = Field(default="")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """Garantiza el cumplimiento estricto del Factor III en producción."""
        if self.environment.lower() == "production":
            insecure_defaults = [
                "change-me-in-development",
                "change-me-in-development-super-secret-key-talentmatch",
                "secret",
                "password",
            ]
            if self.jwt_secret_key in insecure_defaults or len(self.jwt_secret_key) < 32:
                raise ValueError(
                    "Error de seguridad (12-Factor App - Factor III): JWT_SECRET_KEY "
                    "debe ser una clave segura de al menos 32 caracteres (256 bits) definida en producción."
                )
        return self


settings = Settings()

