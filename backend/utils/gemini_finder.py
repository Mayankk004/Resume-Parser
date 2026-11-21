"""Recruiter query decomposition using Google Gemini Structured Outputs."""

import os
from typing import Any, Dict, List
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from utils.parser_helpers import heuristic_parse_query


class ParsedQuerySchema(BaseModel):
    skills: List[str] = Field(default_factory=list, description="Required technical or domain skills")
    work_experience: List[str] = Field(default_factory=list, description="Job roles, companies, or domain keywords")
    education: List[str] = Field(default_factory=list, description="Degrees, fields of study, or institutions")
    certifications: List[str] = Field(default_factory=list, description="Requested certifications or licenses")
    projects: List[str] = Field(default_factory=list, description="Project themes or technical keywords")
    min_gpa: str = Field(default="0", description="Minimum numeric GPA string or '0' if not mentioned")


def _get_genai_client() -> genai.Client | None:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def extract_prompt_info(description: str) -> Dict[str, Any]:
    """Decompose a recruiter search prompt into structured target criteria."""
    client = _get_genai_client()
    if client is None:
        return heuristic_parse_query(description)

    model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip() or "gemini-3.5-flash-lite"
    prompt = (
        "Decompose this recruiter search prompt into structured candidate requirements. "
        "Extract specific skills, target roles/companies, education, certifications, project keywords, "
        "and minimum GPA (return '0' if GPA is not mentioned).\n\n"
        f"Search prompt: {description}"
    )

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ParsedQuerySchema,
            ),
        )
        parsed_obj = response.parsed
        if parsed_obj is None and response.text:
            parsed_obj = ParsedQuerySchema.model_validate_json(response.text)
        if parsed_obj is None:
            return heuristic_parse_query(description)

        return {
            "skills": parsed_obj.skills,
            "work_experience": parsed_obj.work_experience,
            "education": parsed_obj.education,
            "certifications": parsed_obj.certifications,
            "projects": parsed_obj.projects,
            "gpa": parsed_obj.min_gpa or "0",
        }
    except Exception as exc:
        print(f"[WARN] Gemini query decomposition failed ({exc}); using local fallback.")
        return heuristic_parse_query(description)
