"""API routes for batch PDF ingestion, Neon Object Storage, pgvector search, and Neon Realtime."""

import math
import os
import re
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from database import DB_BACKEND, SessionLocal, get_db
from models import Resume
from rate_limiter import limiter
from schemas import (
    BatchFileStatus,
    BatchUploadResponse,
    ResumeResponse,
    SearchMatchItem,
    SearchRequest,
    SearchResponse,
)
from utils.embeddings import generate_document_embedding, generate_query_embedding
from utils.gemini_finder import extract_prompt_info
from utils.gemini_parser import extract_resume_from_pdf_bytes
from utils.parser_helpers import flatten_to_tokens, parse_gpa
from utils.realtime import is_realtime_configured, seal_live_query
from utils.storage import (
    delete_pdf_from_storage,
    get_bucket_name,
    get_presigned_pdf_url,
    is_storage_configured,
    upload_pdf_to_storage,
)

router = APIRouter()

MAX_BATCH_FILES = 10
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

# Read-only deterministic query for Neon Realtime (excludes 768-dim embedding to minimize egress)
LIVE_RESUMES_SQL = (
    "SELECT id, name, email, phone_number, skills, work_experience, education, "
    "certifications, projects, gpa, model_type, status, error_message, file_name, "
    "storage_key, created_at FROM resume ORDER BY id DESC LIMIT 100"
)

_BATCH_LOCK = threading.Lock()
_BATCH_JOBS: Dict[str, List[Dict[str, Any]]] = {}


def _format_item(item: Any) -> str:
    if isinstance(item, dict):
        parts = [f"{k}: {v}" for k, v in item.items() if v not in (None, "", [], {})]
        return " | ".join(parts)
    if isinstance(item, list):
        return ", ".join(str(x) for x in item if x)
    return str(item or "")


def prepare_resume_text(data: dict) -> str:
    """Flatten structured resume fields into rich text for Gemini document embedding."""
    skills = data.get("skills") or {}
    if isinstance(skills, dict):
        skill_parts = []
        for cat, items in skills.items():
            if isinstance(items, list):
                skill_parts.append(f"{cat}: {', '.join(str(x) for x in items)}")
            elif items:
                skill_parts.append(f"{cat}: {items}")
        skills_str = "; ".join(skill_parts)
    elif isinstance(skills, list):
        skills_str = ", ".join(str(x) for x in skills)
    else:
        skills_str = str(skills)

    work_exp_str = "\n  ".join(_format_item(x) for x in (data.get("work_experience") or []))
    edu_str = "\n  ".join(_format_item(x) for x in (data.get("education") or []))
    cert_str = ", ".join(_format_item(x) for x in (data.get("certifications") or []))
    proj_str = "\n  ".join(_format_item(x) for x in (data.get("projects") or []))

    return "\n".join([
        f"Name: {data.get('name', '')}",
        f"Email: {data.get('email', '')}",
        f"Phone: {data.get('phone_number', '')}",
        f"Skills: {skills_str}",
        f"Work Experience:\n  {work_exp_str}",
        f"Education:\n  {edu_str}",
        f"Certifications: {cert_str}",
        f"Projects:\n  {proj_str}",
        f"GPA: {data.get('gpa', '')}",
    ]).strip()


def _to_resume_response(resume: Resume) -> ResumeResponse:
    resp = ResumeResponse.model_validate(resume)
    if resume.storage_key and is_storage_configured():
        try:
            resp.pdf_url = get_presigned_pdf_url(resume.storage_key)
        except Exception as exc:
            print(f"[WARN] Could not presign URL for {resume.storage_key}: {exc}")
    return resp


def _update_batch_item(batch_id: str, index: int, **updates: Any) -> None:
    with _BATCH_LOCK:
        job = _BATCH_JOBS.get(batch_id)
        if job and 0 <= index < len(job):
            job[index].update(updates)


def _with_rate_limit_backoff(fn, *args, max_retries: int = 3, **kwargs):
    delay = 2.0
    for attempt in range(max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            msg = str(exc).lower()
            is_rate_limit = "429" in msg or "resource_exhausted" in msg or "quota" in msg
            if is_rate_limit and attempt < max_retries:
                print(f"[WARN] Gemini rate limit hit; retrying in {delay:.0f}s...")
                time.sleep(delay)
                delay *= 2
                continue
            raise


def upsert_resume_with_embedding(
    db: Session,
    extracted: Dict[str, Any],
    embedding: List[float],
    storage_key: Optional[str] = None,
) -> Resume:
    """Atomically upsert structured resume, Object Storage key, and 768-dim embedding."""
    parsed_email = extracted.get("email")
    existing: Optional[Resume] = None
    if parsed_email:
        existing = db.query(Resume).filter(Resume.email == parsed_email).first()

    if existing:
        old_key = existing.storage_key
        existing.name = extracted.get("name") or existing.name
        existing.phone_number = extracted.get("phone_number")
        existing.skills = extracted.get("skills") or {}
        existing.work_experience = extracted.get("work_experience") or []
        existing.education = extracted.get("education") or []
        existing.certifications = extracted.get("certifications") or []
        existing.projects = extracted.get("projects") or []
        existing.gpa = extracted.get("gpa") or "0"
        existing.model_type = extracted.get("model_type", "gemini")
        existing.status = "completed"
        existing.error_message = None
        existing.file_name = extracted.get("file_name") or existing.file_name
        if storage_key:
            existing.storage_key = storage_key
        existing.embedding = embedding
        db.commit()
        db.refresh(existing)
        if storage_key and old_key and old_key != storage_key:
            delete_pdf_from_storage(old_key)
        return existing

    resume_obj = Resume(
        name=extracted.get("name") or "Unknown Candidate",
        email=parsed_email,
        phone_number=extracted.get("phone_number"),
        skills=extracted.get("skills") or {},
        work_experience=extracted.get("work_experience") or [],
        education=extracted.get("education") or [],
        certifications=extracted.get("certifications") or [],
        projects=extracted.get("projects") or [],
        gpa=extracted.get("gpa") or "0",
        model_type=extracted.get("model_type", "gemini"),
        status="completed",
        error_message=None,
        file_name=extracted.get("file_name"),
        storage_key=storage_key,
        embedding=embedding,
    )
    db.add(resume_obj)
    db.commit()
    db.refresh(resume_obj)
    return resume_obj


def _process_batch_background(batch_id: str, file_payloads: List[Tuple[str, bytes]]) -> None:
    """Process an uploaded PDF batch sequentially: Gemini parse -> S3 upload -> atomic Postgres upsert."""
    for idx, (file_name, pdf_bytes) in enumerate(file_payloads):
        _update_batch_item(batch_id, idx, status="processing")
        db = SessionLocal()
        uploaded_key: Optional[str] = None
        try:
            extracted = _with_rate_limit_backoff(
                extract_resume_from_pdf_bytes,
                pdf_bytes,
                file_name=file_name,
            )
            doc_text = prepare_resume_text(extracted)
            embedding = _with_rate_limit_backoff(generate_document_embedding, doc_text)
            if is_storage_configured():
                uploaded_key = upload_pdf_to_storage(pdf_bytes, file_name)

            saved = upsert_resume_with_embedding(db, extracted, embedding, storage_key=uploaded_key)

            _update_batch_item(
                batch_id,
                idx,
                status="completed",
                resume_id=saved.id,
                candidate_name=saved.name,
                error=None,
            )
            print(f"[INFO] Batch {batch_id}: indexed '{file_name}' as ID {saved.id} ({saved.name}).")
        except Exception as exc:
            db.rollback()
            if uploaded_key:
                delete_pdf_from_storage(uploaded_key)
            _update_batch_item(
                batch_id,
                idx,
                status="failed",
                error=str(exc),
            )
            print(f"[ERROR] Batch {batch_id}: failed '{file_name}': {exc}")
        finally:
            db.close()


@router.get("/config/status")
def get_system_status(db: Session = Depends(get_db)):
    """Return active backend stack status and candidate counts without exposing secrets."""
    total_resumes = db.query(Resume).count()
    completed_resumes = db.query(Resume).filter(Resume.status == "completed").count()
    with _BATCH_LOCK:
        active_queue = sum(
            1
            for items in _BATCH_JOBS.values()
            for item in items
            if item["status"] in ("queued", "processing")
        )

    realtime_url = os.getenv("NEON_REALTIME_URL", "").strip()
    return {
        "database": DB_BACKEND,
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY", "").strip()),
        "gemini_model": os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
        "vector_backend": "pgvector" if DB_BACKEND == "postgresql" else "sqlite_local",
        "storage_configured": is_storage_configured(),
        "storage_bucket": get_bucket_name() if is_storage_configured() else None,
        "realtime_configured": is_realtime_configured(),
        "realtime_url": realtime_url if is_realtime_configured() else None,
        "total_resumes": total_resumes,
        "completed_resumes": completed_resumes,
        "processing_resumes": active_queue,
    }


@router.post("/resumes/live")
def seal_resumes_live_query():
    """Seal the read-only candidate repository query for Neon Realtime subscription."""
    if not is_realtime_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neon Realtime is not configured.",
        )
    debug_mode = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    sealed = seal_live_query(LIVE_RESUMES_SQL, debug_mode=debug_mode)
    return {
        "realtimeUrl": os.getenv("NEON_REALTIME_URL", "").strip(),
        "sealedQuery": sealed,
    }


@router.get("/resumes/", response_model=List[ResumeResponse])
def list_resumes(db: Session = Depends(get_db)):
    """List all parsed resumes ordered by newest first."""
    rows = db.query(Resume).order_by(Resume.id.desc()).all()
    return [ResumeResponse.model_validate(row) for row in rows]


def get_resume_by_id(db: Session, resume_id: int) -> Optional[Resume]:
    """Fetch a single resume record from the database by ID."""
    return db.query(Resume).filter(Resume.id == resume_id).first()


@router.get("/resume/{resume_id}", response_model=ResumeResponse)
def get_resume(resume_id: int, db: Session = Depends(get_db)):
    """Retrieve a parsed resume by ID with a presigned Neon Object Storage PDF URL if stored."""
    resume = get_resume_by_id(db, resume_id)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )
    return _to_resume_response(resume)


@router.delete("/resume/{resume_id}")
def delete_resume(resume_id: int, db: Session = Depends(get_db)):
    """Delete a resume record from PostgreSQL and its PDF object from Neon Object Storage."""
    resume = get_resume_by_id(db, resume_id)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )
    storage_key = resume.storage_key
    db.delete(resume)
    db.commit()
    if storage_key:
        delete_pdf_from_storage(storage_key)
    return {"status": "deleted", "id": resume_id}


@router.post("/resume/", response_model=BatchUploadResponse)
@limiter.limit("10/minute")
async def upload_resumes(
    request: Request,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
):
    """Accept up to 10 PDF resumes (max 5 MB each) and process them asynchronously in memory."""
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one PDF file is required.",
        )
    if len(files) > MAX_BATCH_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_BATCH_FILES} files allowed per batch upload.",
        )

    file_payloads: List[Tuple[str, bytes]] = []
    initial_statuses: List[Dict[str, Any]] = []

    for uploaded in files:
        file_name = os.path.basename(uploaded.filename or "resume.pdf")
        content_type = (uploaded.content_type or "").lower()
        if not file_name.lower().endswith(".pdf") and content_type != "application/pdf":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file '{file_name}'. Only PDF files are supported.",
            )

        raw_bytes = await uploaded.read()
        if not raw_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Uploaded file '{file_name}' is empty.",
            )
        if len(raw_bytes) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{file_name}' exceeds the 5 MB limit.",
            )

        file_payloads.append((file_name, raw_bytes))
        initial_statuses.append({
            "file_name": file_name,
            "status": "queued",
            "resume_id": None,
            "candidate_name": None,
            "error": None,
        })

    batch_id = uuid.uuid4().hex
    with _BATCH_LOCK:
        _BATCH_JOBS[batch_id] = initial_statuses

    background_tasks.add_task(_process_batch_background, batch_id, file_payloads)

    return BatchUploadResponse(
        batch_id=batch_id,
        files=[BatchFileStatus(**item) for item in initial_statuses],
    )


@router.get("/resume/batch/{batch_id}", response_model=BatchUploadResponse)
def get_batch_status(batch_id: str):
    """Return live per-file processing status for a batch upload."""
    with _BATCH_LOCK:
        job = _BATCH_JOBS.get(batch_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Batch ID not found.",
            )
        snapshot = [BatchFileStatus(**item) for item in job]

    return BatchUploadResponse(batch_id=batch_id, files=snapshot)


def _cosine_distance_py(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 1.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 1.0
    sim = max(-1.0, min(1.0, dot / (na * nb)))
    return 1.0 - sim


def _score_candidate(
    resume: Resume,
    extracted_prompt_info: Dict[str, Any],
    semantic_similarity: float,
    prompt_text: str,
) -> SearchMatchItem:
    """Compute hybrid semantic + structured criteria match score with matched/missing skills."""
    candidate_fields = {
        "skills": flatten_to_tokens(resume.skills),
        "work_experience": flatten_to_tokens(resume.work_experience),
        "education": flatten_to_tokens(resume.education),
        "certifications": flatten_to_tokens(resume.certifications),
        "projects": flatten_to_tokens(resume.projects),
    }
    all_candidate_tokens: Set[str] = set()
    for token_set in candidate_fields.values():
        all_candidate_tokens.update(token_set)

    matched_skills: List[str] = []
    missing_skills: List[str] = []
    matched_criteria: List[str] = []
    keyword_hits = 0
    total_criteria = 0

    for req_skill in extracted_prompt_info.get("skills") or []:
        req_clean = str(req_skill).strip()
        if not req_clean:
            continue
        total_criteria += 1
        if req_clean.lower() in all_candidate_tokens:
            keyword_hits += 1
            matched_skills.append(req_clean)
            matched_criteria.append(req_clean)
        else:
            missing_skills.append(req_clean)

    for field_name in ("work_experience", "education", "certifications", "projects"):
        for req in extracted_prompt_info.get(field_name) or []:
            req_clean = str(req).strip()
            if not req_clean:
                continue
            total_criteria += 1
            if req_clean.lower() in all_candidate_tokens:
                keyword_hits += 1
                if req_clean not in matched_criteria:
                    matched_criteria.append(req_clean)

    prompt_words = {
        w for w in re.findall(r"[a-z0-9+#.]{2,}", prompt_text.lower())
        if w not in {"with", "and", "for", "the", "looking", "candidate", "developer", "engineer", "years"}
    }
    direct_overlap = prompt_words & all_candidate_tokens
    for word in sorted(direct_overlap):
        if word not in {c.lower() for c in matched_criteria}:
            matched_criteria.append(word)

    req_gpa = parse_gpa(extracted_prompt_info.get("gpa"))
    cand_gpa = parse_gpa(resume.gpa)
    if req_gpa is not None:
        total_criteria += 1
        if cand_gpa is not None and cand_gpa >= req_gpa:
            keyword_hits += 1
            matched_criteria.append(f"GPA {cand_gpa} >= {req_gpa}")

    semantic_clamped = max(0.0, min(semantic_similarity, 1.0))
    if total_criteria > 0:
        criteria_ratio = keyword_hits / total_criteria
        blended = round((0.50 * semantic_clamped + 0.50 * criteria_ratio) * 100, 1)
    else:
        blended = round(semantic_clamped * 100, 1)

    return SearchMatchItem(
        resume=_to_resume_response(resume),
        match_score=blended,
        semantic_score=round(semantic_clamped * 100, 1),
        keyword_score=keyword_hits + len(direct_overlap),
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        matched_criteria=matched_criteria[:12],
    )


@router.post("/search-resume/", response_model=SearchResponse)
@limiter.limit("20/minute")
async def process_resume_search_rag(
    request: Request,
    payload: SearchRequest,
    db: Session = Depends(get_db),
):
    """Search candidates using PostgreSQL pgvector cosine distance + Gemini criteria re-ranking."""
    total_completed = db.query(Resume).filter(Resume.status == "completed").count()
    if total_completed == 0:
        return SearchResponse(
            query=payload.user_prompt,
            extracted_criteria={},
            total_candidates=0,
            results=[],
            message="No resumes indexed yet. Upload PDF resumes or seed demo candidates first.",
        )

    query_embedding = _with_rate_limit_backoff(generate_query_embedding, payload.user_prompt)

    candidate_pairs: List[Tuple[Resume, float]] = []
    if DB_BACKEND == "postgresql":
        distance_col = Resume.embedding.cosine_distance(query_embedding).label("distance")
        rows = (
            db.query(Resume, distance_col)
            .filter(Resume.status == "completed", Resume.embedding.isnot(None))
            .order_by(distance_col)
            .limit(10)
            .all()
        )
        candidate_pairs = [(res, max(0.0, 1.0 - float(dist))) for res, dist in rows]
    else:
        rows = (
            db.query(Resume)
            .filter(Resume.status == "completed", Resume.embedding.isnot(None))
            .all()
        )
        scored_py = [
            (res, max(0.0, 1.0 - _cosine_distance_py(list(res.embedding), query_embedding)))
            for res in rows
        ]
        scored_py.sort(key=lambda pair: pair[1], reverse=True)
        candidate_pairs = scored_py[:10]

    extracted_prompt_info = extract_prompt_info(payload.user_prompt)

    ranked = [
        _score_candidate(
            resume=res,
            extracted_prompt_info=extracted_prompt_info,
            semantic_similarity=sim,
            prompt_text=payload.user_prompt,
        )
        for res, sim in candidate_pairs
    ]

    ranked.sort(
        key=lambda item: (item.match_score, item.semantic_score, item.keyword_score),
        reverse=True,
    )

    top_results = ranked[: min(payload.top_k, 5)]
    return SearchResponse(
        query=payload.user_prompt,
        extracted_criteria=extracted_prompt_info,
        total_candidates=total_completed,
        results=top_results,
        message=None if top_results else "No matching candidates with embeddings found.",
    )
