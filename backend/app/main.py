"""FastAPI application entry point."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, conversations, documents, health, orders, tickets, users
from app.core.config import get_settings
from app.core.exceptions import AppError

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="AI customer-support platform: orders, support tickets and (phase 2) a RAG-powered agent.",
    version="0.1.0",
)

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
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=headers)


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(orders.router)
app.include_router(tickets.router)
app.include_router(conversations.router)
app.include_router(documents.router)
