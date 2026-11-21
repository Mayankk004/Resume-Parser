"""Database configuration, Neon pooled vs direct connections, and pgvector initialization."""

import os
from pathlib import Path
from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent


def load_project_env() -> None:
    """Load backend/.env and root .env.local without overwriting populated keys with blanks."""
    merged: dict[str, str] = {}
    for candidate in (BACKEND_DIR / ".env", ROOT_DIR / ".env", ROOT_DIR / ".env.local"):
        if candidate.exists():
            for k, v in dotenv_values(candidate).items():
                if v is not None and v.strip() != "":
                    merged[k] = v.strip()
    for k, v in merged.items():
        if not os.environ.get(k):
            os.environ[k] = v


load_project_env()

Base = declarative_base()


def _normalize_pg_url(url: str) -> str:
    cleaned = (url or "").strip()
    if cleaned.startswith("postgres://"):
        cleaned = "postgresql+psycopg2://" + cleaned[len("postgres://"):]
    elif cleaned.startswith("postgresql://"):
        cleaned = "postgresql+psycopg2://" + cleaned[len("postgresql://"):]
    return cleaned


POOLED_DATABASE_URL = _normalize_pg_url(os.getenv("DATABASE_URL", ""))
DIRECT_DATABASE_URL = _normalize_pg_url(os.getenv("DATABASE_URL_UNPOOLED", "")) or POOLED_DATABASE_URL

DATA_DIR = BACKEND_DIR / "data"
SQLITE_PATH = DATA_DIR / "resume_parser.db"


def _create_active_engine():
    """Use Neon pooled DATABASE_URL for runtime queries, with SQLite fallback if unset."""
    if POOLED_DATABASE_URL:
        pg_engine = create_engine(
            POOLED_DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=300,
        )
        print("[INFO] Configured Neon PostgreSQL pooled runtime engine.")
        return pg_engine, "postgresql"

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    sqlite_engine = create_engine(
        f"sqlite:///{SQLITE_PATH.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    print(f"[WARN] DATABASE_URL not set. Using local SQLite fallback at {SQLITE_PATH}.")
    return sqlite_engine, "sqlite"


engine, DB_BACKEND = _create_active_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables() -> bool:
    """Run DDL migrations over direct/unpooled connection (recommended by Neon best practices)."""
    try:
        if DB_BACKEND == "postgresql":
            ddl_engine = (
                create_engine(DIRECT_DATABASE_URL, pool_pre_ping=True)
                if DIRECT_DATABASE_URL and DIRECT_DATABASE_URL != POOLED_DATABASE_URL
                else engine
            )
            try:
                with ddl_engine.begin() as conn:
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                Base.metadata.create_all(bind=ddl_engine)
                with ddl_engine.begin() as conn:
                    conn.execute(
                        text("ALTER TABLE resume ADD COLUMN IF NOT EXISTS storage_key VARCHAR;")
                    )
            finally:
                if ddl_engine is not engine:
                    ddl_engine.dispose()
        else:
            Base.metadata.create_all(bind=engine)
        print(f"[INFO] Database tables verified/created successfully ({DB_BACKEND}).")
        return True
    except Exception as exc:
        print(f"[ERROR] Error creating tables: {exc}")
        return False


def get_db():
    """FastAPI dependency yielding a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
