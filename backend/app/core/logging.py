"""Structured JSON logging with a request id.

Every log line is one JSON object, e.g.
  {"time": "...", "level": "INFO", "logger": "supportai.tools", "message": "tool call",
   "request_id": "3f2a…", "tool": "get_order_status", "ok": true, "duration_ms": 4}

What we never log: passwords, tokens, API keys, request headers or bodies, query strings, chat text.
Code passes only safe fields in `extra={...}`.
"""

import json
import logging
import re
import time
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

# Attributes every LogRecord has; anything else came from `extra={...}`.
_STANDARD_ATTRS = set(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {"message", "asctime", "taskName"}
_SENSITIVE_KEY = re.compile(r"pass(word)?|secret|token|api[_-]?key|authorization", re.IGNORECASE)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if request_id := request_id_var.get():
            entry["request_id"] = request_id
        for key, value in vars(record).items():
            if key not in _STANDARD_ATTRS and not key.startswith("_"):
                # Belt and braces: even if someone passes a secret by mistake, it's redacted.
                entry[key] = "[redacted]" if _SENSITIVE_KEY.search(key) else value
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    # Uvicorn's own access log would duplicate our request log (and includes query strings).
    logging.getLogger("uvicorn.access").disabled = True
    for noisy in ("httpx", "httpcore", "anthropic"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Assigns a request id, logs method, path, status and latency for every request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get("x-request-id", "")
        request_id = incoming if re.fullmatch(r"[A-Za-z0-9-]{8,64}", incoming) else uuid.uuid4().hex
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        logger = logging.getLogger("supportai.http")
        try:
            response = await call_next(request)
            logger.info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000),
                },
            )
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            logger.exception("unhandled error", extra={"method": request.method, "path": request.url.path})
            raise
        finally:
            request_id_var.reset(token)
