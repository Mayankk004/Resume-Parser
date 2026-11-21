"""Pydantic schemas for API request validation, batch status, and search responses."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class ResumeBase(BaseModel):
    name: str
    email: Optional[str] = None
    phone_number: Optional[str] = None
    skills: Union[Dict[str, Any], List[Any], None] = Field(default_factory=dict)
    work_experience: Optional[List[Any]] = Field(default_factory=list)
    education: Optional[List[Any]] = Field(default_factory=list)
    certifications: Optional[List[Any]] = Field(default_factory=list)
    projects: Optional[List[Any]] = Field(default_factory=list)
    gpa: Optional[str] = "0"
    model_type: str = "gemini"
    status: str = "completed"
    error_message: Optional[str] = None
    file_name: Optional[str] = None
    storage_key: Optional[str] = None


class ResumeCreate(ResumeBase):
    pass


class ResumeResponse(ResumeBase):
    id: int
    pdf_url: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BatchFileStatus(BaseModel):
    file_name: str
    status: str  # queued | processing | completed | failed
    resume_id: Optional[int] = None
    candidate_name: Optional[str] = None
    error: Optional[str] = None


class BatchUploadResponse(BaseModel):
    batch_id: str
    files: List[BatchFileStatus]


class SearchRequest(BaseModel):
    user_prompt: str = Field(..., min_length=1, description="Natural language candidate search query")
    top_k: int = Field(default=5, ge=1, le=20)


class SearchMatchItem(BaseModel):
    resume: ResumeResponse
    match_score: float
    semantic_score: float
    keyword_score: int
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    matched_criteria: List[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    query: str
    extracted_criteria: Dict[str, Any] = Field(default_factory=dict)
    total_candidates: int = 0
    results: List[SearchMatchItem] = Field(default_factory=list)
    message: Optional[str] = None
