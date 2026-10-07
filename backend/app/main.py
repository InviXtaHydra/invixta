"""FastAPI application entry point."""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, chat, conversations, documents, health, knowledge_base, orders, tickets, users
from app.core.config import get_settings
from app.core.exceptions import AppError, TooManyRequestsError
from app.core.logging import RequestLoggingMiddleware, configure_logging

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title=settings.app_name,
    description="AI customer-support platform: orders, support tickets, a RAG knowledge base and a tool-calling AI agent.",
    version="1.0.0",
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,  # we use bearer tokens, not cookies
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(AppError)
def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
    """Turn domain errors from the service layer into JSON responses with the right status code."""
    headers: dict[str, str] = {}
    if exc.status_code == 401:
        headers["WWW-Authenticate"] = "Bearer"
    if isinstance(exc, TooManyRequestsError):
        headers["Retry-After"] = str(exc.retry_after)
    if exc.status_code >= 500:
        logging.getLogger("supportai.errors").error("service error", extra={"status": exc.status_code, "error": type(exc).__name__})
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=headers or None)


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(orders.router)
app.include_router(tickets.router)
app.include_router(conversations.router)
app.include_router(documents.router)
app.include_router(knowledge_base.router)
app.include_router(chat.router)
