from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ToolUsageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    calls: int
    errors: int


class UnresolvedQuestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    conversation_id: int
    question: str | None
    answered_at: datetime


class DayCountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    day: date
    count: int


class TopProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    units: int


class SalesRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    orders: int = Field(description="Orders that weren't cancelled")
    cancelled_orders: int
    revenue_eur: Decimal = Field(description="Total of paid orders; refunded orders don't count")
    average_order_value_eur: Decimal | None
    items_sold: int
    top_products: list[TopProductRead]
    low_stock_sizes: int = Field(description="Sizes of products in the shop with 3 or fewer left")
    orders_per_day: list[DayCountRead]


class MetricsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_conversations: int
    chat_turns: int = Field(description="Questions answered by the assistant")
    avg_latency_ms: float | None = Field(description="Average time to answer a chat message (agent + tools + LLM)")
    p95_latency_ms: float | None
    tool_calls: int
    tool_usage: list[ToolUsageRead]
    rag_searches: int = Field(description="Knowledge-base searches made by the agent")
    tickets_total: int
    tickets_by_status: dict[str, int]
    unresolved_questions: int = Field(description="Answers that said the knowledge base didn't have the answer, or that failed")
    recent_unresolved: list[UnresolvedQuestionRead]
    chat_turns_per_day: list[DayCountRead]
    sales: SalesRead
