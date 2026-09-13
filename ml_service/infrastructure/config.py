from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    database_url: str = "postgresql+asyncpg://talentmatch:talentmatch@localhost:5432/talentmatch"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

