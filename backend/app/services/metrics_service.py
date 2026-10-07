"""Usage metrics for the admin dashboard, computed with SQL from what the chat already stores:
every assistant message has its latency, tool calls and sources (see ChatService)."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import ColumnElement, column, func, or_, select, true
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session, aliased

from app.agents.support_agent import FALLBACK_REPLY
from app.models import Conversation, Message, MessageRole, SupportTicket, TicketStatus
from app.rag.rag_service import NOT_FOUND_MESSAGE


@dataclass
class ToolUsage:
    name: str
    calls: int
    errors: int


@dataclass
class UnresolvedQuestion:
    conversation_id: int
    question: str | None
    answered_at: datetime


@dataclass
class DayCount:
    day: date
    chat_turns: int


@dataclass
class Metrics:
    total_conversations: int
    chat_turns: int
    avg_latency_ms: float | None
    p95_latency_ms: float | None
    tool_calls: int
    tool_usage: list[ToolUsage]
    rag_searches: int
    tickets_total: int
    tickets_by_status: dict[str, int]
    unresolved_questions: int
    recent_unresolved: list[UnresolvedQuestion]
    chat_turns_per_day: list[DayCount]


def is_unresolved() -> ColumnElement[bool]:
    """Assistant answers that admit they couldn't help: the not-found message or the fallback reply."""
    return or_(Message.content.ilike(f"%{NOT_FOUND_MESSAGE.rstrip('.')}%"), Message.content == FALLBACK_REPLY)


class MetricsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def collect(self, days: int = 14) -> Metrics:
        tool_usage = self._tool_usage()
        tickets = self._tickets_by_status()
        avg_latency, p95_latency = self._latency()
        return Metrics(
            total_conversations=self.db.scalar(select(func.count()).select_from(Conversation)) or 0,
            chat_turns=self._count_answers(),
            avg_latency_ms=avg_latency,
            p95_latency_ms=p95_latency,
            tool_calls=sum(t.calls for t in tool_usage),
            tool_usage=tool_usage,
            rag_searches=next((t.calls for t in tool_usage if t.name == "search_knowledge_base"), 0),
            tickets_total=sum(tickets.values()),
            tickets_by_status=tickets,
            unresolved_questions=self._count_answers(is_unresolved()),
            recent_unresolved=self._recent_unresolved(),
            chat_turns_per_day=self._per_day(days),
        )

    def _count_answers(self, *conditions: ColumnElement[bool]) -> int:
        query = select(func.count()).select_from(Message).where(Message.role == MessageRole.ASSISTANT, *conditions)
        return self.db.scalar(query) or 0

    def _latency(self) -> tuple[float | None, float | None]:
        avg, p95 = self.db.execute(
            select(func.avg(Message.latency_ms), func.percentile_cont(0.95).within_group(Message.latency_ms)).where(
                Message.role == MessageRole.ASSISTANT, Message.latency_ms.is_not(None)
            )
        ).one()
        return (round(float(avg), 1) if avg is not None else None, round(float(p95), 1) if p95 is not None else None)

    def _tool_usage(self) -> list[ToolUsage]:
        # jsonb_array_elements turns each message's tool_calls array into one row per tool call:
        #   SELECT call.value->>'name', count(*) FROM messages JOIN jsonb_array_elements(messages.tool_calls) AS call ON true …
        call = func.jsonb_array_elements(Message.tool_calls).table_valued(column("value", JSONB)).alias("call")
        name = call.c.value["name"].astext
        rows = self.db.execute(
            select(name, func.count(), func.count().filter(call.c.value["status"].astext == "error"))
            .select_from(Message)
            .join(call, true())
            .where(func.jsonb_typeof(Message.tool_calls) == "array")
            .group_by(name)
            .order_by(func.count().desc(), name)
        ).all()
        return [ToolUsage(name=n, calls=c, errors=e) for n, c, e in rows]

    def _tickets_by_status(self) -> dict[str, int]:
        rows = self.db.execute(select(SupportTicket.status, func.count()).group_by(SupportTicket.status)).all()
        return {s.value: 0 for s in TicketStatus} | {s.value: n for s, n in rows}

    def _recent_unresolved(self, limit: int = 10) -> list[UnresolvedQuestion]:
        """The latest answers that couldn't help, with the customer question that came right before."""
        question = aliased(Message)
        asked = (
            select(question.content)
            .where(question.conversation_id == Message.conversation_id, question.role == MessageRole.USER, question.id < Message.id)
            .order_by(question.id.desc())
            .limit(1)
            .correlate(Message)
            .scalar_subquery()
        )
        rows = self.db.execute(
            select(Message.conversation_id, asked, Message.created_at)
            .where(Message.role == MessageRole.ASSISTANT, is_unresolved())
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
        ).all()
        return [UnresolvedQuestion(conversation_id=c, question=q, answered_at=t) for c, q, t in rows]

    def _per_day(self, days: int) -> list[DayCount]:
        """Chat answers per day for the last `days` days (UTC), including days without any."""
        first_day = datetime.now(UTC).date() - timedelta(days=days - 1)
        day = func.date(func.timezone("UTC", Message.created_at))
        rows = self.db.execute(
            select(day, func.count())
            .where(Message.role == MessageRole.ASSISTANT, Message.created_at >= datetime.combine(first_day, datetime.min.time(), UTC))
            .group_by(day)
        ).all()
        counts: dict[date, int] = {d: n for d, n in rows}
        return [DayCount(day=d, chat_turns=counts.get(d, 0)) for d in (first_day + timedelta(days=i) for i in range(days))]
