"""Application settings, read from environment variables (and a local .env file)."""

from decimal import Decimal
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Invixta"
    environment: str = "development"

    database_url: str = Field(..., description="SQLAlchemy URL, e.g. postgresql+psycopg://user:pw@host/db")

    jwt_secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # Origins allowed to call the API from a browser directly (the React app uses a same-origin proxy).
    # NoDecode: read "a,b" as plain text and split it ourselves instead of expecting JSON.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    # --- RAG + AI agent -------------------------------------------------------------
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    embedding_cache_dir: str | None = None  # where the model files live (baked into the Docker image)

    # Retrieval: how many chunks to fetch, and the minimum cosine similarity to count as relevant.
    rag_top_k: int = 5
    rag_min_score: float = 0.64

    # LLM: a local model served by Ollama (free, runs on your own machine).
    # "scripted" = a deterministic rule-based stand-in for the end-to-end tests in CI
    # (app/agents/scripted_llm.py); refused when ENVIRONMENT=production.
    llm_provider: Literal["ollama", "scripted"] = "ollama"
    ollama_url: str = "http://localhost:11434"  # in Docker: http://host.docker.internal:11434
    llm_model: str = "qwen3:8b"
    llm_temperature: float = 0.2
    llm_context_tokens: int = 8192  # context window: system prompt + tools + history + sources must fit
    llm_max_tokens: int = 1024  # maximum length of one answer
    llm_think: bool = False  # qwen3 "thinking" mode: better reasoning, but much slower on a laptop
    llm_timeout_seconds: int = 300
    agent_max_tool_rounds: int = 6
    # The agent searches the knowledge base itself before the model answers (small local models often skip
    # the search tool), and both the agent and /knowledge-base/ask rewrite the question into an English query.
    agent_search_first: bool = True
    rag_query_rewrite: bool = True
    chat_history_messages: int = 20  # earlier messages sent to the model for context

    # Document uploads
    max_upload_mb: int = 10
    max_pdf_pages: int = 200

    log_level: str = "INFO"

    # --- Shop ---------------------------------------------------------------------------------
    personalization_price: Decimal = Decimal("15.00")  # name + number printed on a shirt
    free_shipping_from: Decimal = Decimal("50.00")  # standard shipping is free from this subtotal
    shipping_benelux: Decimal = Decimal("4.95")
    shipping_eu: Decimal = Decimal("9.95")
    express_surcharge: Decimal = Decimal("7.50")  # express: next working day, NL and BE only
    # The fulfillment simulator (scripts/fulfillment_simulator.py) plays the warehouse and the carrier,
    # in minutes instead of days so you can watch an order move through its statuses.
    simulation_ship_after_minutes: float = 3
    simulation_deliver_after_minutes: float = 10
    simulation_payment_timeout_minutes: float = 30  # unpaid orders are cancelled after this
    # Only orders placed in the last N hours are shipped and delivered by the simulator, so the older demo
    # orders from the seed keep their story (e.g. "shipped three days ago, arriving tomorrow").
    simulation_recent_hours: float = 24

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
    def safe_production_settings(self) -> "Settings":
        if self.environment != "production":
            return self
        if self.llm_provider == "scripted":
            raise ValueError("LLM_PROVIDER=scripted is only for tests and can't be used with ENVIRONMENT=production")
        if "change-me" in self.jwt_secret_key:
            raise ValueError("JWT_SECRET_KEY still has the placeholder value from .env.example; generate a real secret")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # values come from the environment
