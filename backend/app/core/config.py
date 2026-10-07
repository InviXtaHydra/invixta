"""Application settings, read from environment variables (and a local .env file)."""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
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

    # --- Phase 2: RAG + AI agent -------------------------------------------------------------
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    embedding_cache_dir: str | None = None  # where the model files live (baked into the Docker image)

    # Retrieval: how many chunks to fetch, and the minimum cosine similarity to count as relevant.
    rag_top_k: int = 5
    rag_min_score: float = 0.6

    # LLM (Claude). Without an API key the chat and RAG-answer endpoints return 503.
    # "anthropic" = Claude. "scripted" = a deterministic rule-based stand-in for the end-to-end tests
    # (app/agents/scripted_llm.py); refused when ENVIRONMENT=production.
    llm_provider: Literal["anthropic", "scripted"] = "anthropic"
    anthropic_api_key: str | None = None
    llm_model: str = "claude-opus-5-5"
    llm_effort: str = "medium"  # low | medium | high — trades answer depth against latency and cost
    llm_max_tokens: int = 16000
    agent_max_tool_rounds: int = 6
    chat_history_messages: int = 20  # earlier messages sent to the model for context

    # Document uploads
    max_upload_mb: int = 10
    max_pdf_pages: int = 200

    log_level: str = "INFO"

    # Simple per-process rate limits (see app/core/rate_limit.py)
    login_attempts_per_minute: int = 10
    chat_messages_per_minute: int = 20

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        # Allow CORS_ORIGINS="http://a,http://b" in .env files.
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def no_test_llm_in_production(self) -> "Settings":
        if self.environment == "production" and self.llm_provider == "scripted":
            raise ValueError("LLM_PROVIDER=scripted is only for tests and can't be used with ENVIRONMENT=production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # values come from the environment
