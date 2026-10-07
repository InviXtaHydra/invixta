"""Application settings, read from environment variables (and a local .env file)."""

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "SupportAI"
    environment: str = "development"

    database_url: str = Field(..., description="SQLAlchemy URL, e.g. postgresql+psycopg://user:pw@host/db")

    jwt_secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # NoDecode: read "a,b" as plain text and split it ourselves instead of expecting JSON.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    embedding_dim: int = 384

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        # Allow CORS_ORIGINS="http://a,http://b" in .env files.
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # values come from the environment
