"""SQLAlchemy ORM models for resume metadata, Object Storage keys, and pgvector embeddings."""

from datetime import datetime, timezone
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Index, Integer, JSON, String, Text
from database import Base


class Resume(Base):
    """Represents a parsed candidate resume, its Object Storage PDF key, and 768-dim embedding."""

    __tablename__ = "resume"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, default="Unknown Candidate")
    email = Column(String, unique=True, nullable=True, index=True)
    phone_number = Column(String, nullable=True)
    skills = Column(JSON, nullable=False, default=dict)
    work_experience = Column(JSON, nullable=True, default=list)
    education = Column(JSON, nullable=False, default=list)
    certifications = Column(JSON, nullable=True, default=list)
    projects = Column(JSON, nullable=False, default=list)
    gpa = Column(String, nullable=True, default="0")
    model_type = Column(String, nullable=False, default="gemini")
    status = Column(String, nullable=False, default="completed")
    error_message = Column(Text, nullable=True)
    file_name = Column(String, nullable=True)
    storage_key = Column(String, nullable=True)
    embedding = Column(Vector(768), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index(
            "ix_resume_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
