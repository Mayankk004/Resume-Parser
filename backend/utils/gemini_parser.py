"""PDF resume parser sending raw PDF bytes directly to Google Gemini Structured Outputs."""

import os
from typing import Any, Dict, List, Optional
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from utils.parser_helpers import normalize_resume_data


class SkillGroupSchema(BaseModel):
    category: str = Field(description="Skill category such as Languages, Frameworks, Cloud, Tools")
    items: List[str] = Field(default_factory=list)


class WorkExperienceSchema(BaseModel):
    Company: str = ""
    Position: str = ""
    Duration: str = ""
    Description: str = ""


class EducationSchema(BaseModel):
    Degree: str = ""
    Institution: str = ""
    Year: str = ""


class CertificationSchema(BaseModel):
    Name: str = ""
    Issuer: str = ""


class ProjectSchema(BaseModel):
    Name: str = ""
    Description: str = ""


class ParsedResumeSchema(BaseModel):
    Name: str = Field(description="Candidate full name")
    Email: Optional[str] = Field(default=None, description="Candidate email address if present")
    Phone_Number: Optional[str] = Field(default=None, description="Candidate phone number if present")
    Skills: List[SkillGroupSchema] = Field(default_factory=list)
    Work_Experience: List[WorkExperienceSchema] = Field(default_factory=list)
    Education: List[EducationSchema] = Field(default_factory=list)
    Certifications: List[CertificationSchema] = Field(default_factory=list)
    Projects: List[ProjectSchema] = Field(default_factory=list)
    Gpa: str = Field(default="0", description="Numeric GPA/CGPA string or '0' if not mentioned")


def _get_genai_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")
    return genai.Client(api_key=api_key)


def extract_resume_from_pdf_bytes(pdf_bytes: bytes, file_name: str = "resume.pdf") -> Dict[str, Any]:
    """Send raw PDF bytes directly to Gemini Structured Outputs to extract resume fields."""
    client = _get_genai_client()
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip() or "gemini-3.5-flash-lite"

    prompt = (
        "Extract all structured candidate details accurately from the attached PDF resume. "
        "Group skills logically by category. Return '0' for Gpa if not mentioned, and null "
        "for Email or Phone_Number if absent."
    )

    response = client.models.generate_content(
        model=model_name,
        contents=[
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            prompt,
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ParsedResumeSchema,
        ),
    )

    parsed_obj = response.parsed
    if parsed_obj is None and response.text:
        parsed_obj = ParsedResumeSchema.model_validate_json(response.text)
    if parsed_obj is None:
        raise ValueError("Gemini returned an empty response for PDF extraction.")

    skills_dict = {
        group.category: [item for item in group.items if item.strip()]
        for group in parsed_obj.Skills
        if group.items
    }

    raw_dict = {
        "Name": parsed_obj.Name,
        "Email": parsed_obj.Email,
        "Phone Number": parsed_obj.Phone_Number,
        "Skills": skills_dict,
        "Work Experience": [exp.model_dump() for exp in parsed_obj.Work_Experience],
        "Education": [edu.model_dump() for edu in parsed_obj.Education],
        "Certifications": [cert.model_dump() for cert in parsed_obj.Certifications],
        "Projects": [proj.model_dump() for proj in parsed_obj.Projects],
        "Gpa": parsed_obj.Gpa or "0",
    }

    fallback_name = file_name.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").strip() or "Unknown Candidate"
    normalized = normalize_resume_data(raw_dict, fallback_name=fallback_name)
    normalized["model_type"] = "gemini"
    normalized["file_name"] = file_name
    return normalized
