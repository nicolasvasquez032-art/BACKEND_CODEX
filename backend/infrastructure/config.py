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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

