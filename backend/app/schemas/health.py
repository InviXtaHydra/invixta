from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    database: str
    llm: str = Field(description='"ok", "model_missing" (run `ollama pull <model>`), "unreachable" (start Ollama) or "scripted"')
    llm_model: str
