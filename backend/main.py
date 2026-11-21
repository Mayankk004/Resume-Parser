"""FastAPI entry point for ResumeParserAI."""

import os
import time
from contextlib import asynccontextmanager
from typing import List

from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from pydantic_settings import BaseSettings, SettingsConfigDict
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

# database.py loads backend/.env and root .env.local cleanly before settings initialization
from database import DB_BACKEND, create_tables, get_db
from rate_limiter import limiter
from routes import resume


def _parse_csv_env(raw: str, default: List[str], strip_slash: bool = False) -> List[str]:
    if not raw or not raw.strip():
        return default
    items = []
    for part in raw.split(","):
        cleaned = part.strip()
        if strip_slash:
            cleaned = cleaned.rstrip("/")
        if cleaned:
            items.append(cleaned)
    return items or default


class Settings(BaseSettings):
    app_name: str = "ResumeParserAI API"
    app_version: str = "3.0.0"

    database_url: str = ""
    database_url_unpooled: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"

    allowed_origins: str = "http://localhost:3000,http://localhost:5173"
    allowed_hosts: str = "*"
    debug: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
cors_origins = _parse_csv_env(
    settings.allowed_origins,
    default=["http://localhost:3000", "http://localhost:5173"],
    strip_slash=True,
)
trusted_hosts = _parse_csv_env(settings.allowed_hosts, default=["*"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize pgvector extension and database tables on startup."""
    create_tables()
    print(f"[INFO] {settings.app_name} v{settings.app_version} started ({DB_BACKEND}).")
    yield
    print(f"[INFO] {settings.app_name} shutting down.")


app = FastAPI(
    title=settings.app_name,
    description="AI Resume Extraction and Hybrid Neon pgvector + Object Storage + Realtime API",
    version=settings.app_version,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if not settings.debug and "*" not in trusted_hosts:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=trusted_hosts,
    )


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{time.time() - start_time:.4f}"
    return response


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Database error occurred", "error": str(exc)},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred", "error": str(exc)},
    )


app.include_router(resume.router, prefix="/api/v1", tags=["Resume"])


@app.get("/", tags=["Root"])
def root():
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "database_backend": DB_BACKEND,
    }


@app.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "database_backend": DB_BACKEND,
        "version": settings.app_version,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
