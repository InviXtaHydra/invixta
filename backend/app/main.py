"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.core.config import get_settings

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

app.include_router(health.router)
