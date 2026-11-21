"""Shared parsing, JSON extraction, normalization, and local heuristic fallback utilities."""

import json
import re
from typing import Any, Dict, List, Optional, Set


KNOWN_SKILLS = [
    "python", "javascript", "typescript", "java", "c++", "c#", "go", "golang", "rust",
    "ruby", "php", "swift", "kotlin", "scala", "r", "sql", "html", "css", "sass",
    "react", "react.js", "next.js", "nextjs", "vue", "angular", "svelte", "node.js",
    "nodejs", "express", "fastapi", "django", "flask", "spring boot", "graphql",
    "rest api", "restful", "postgresql", "postgres", "mysql", "mongodb", "redis",
    "sqlite", "pinecone", "chroma", "weaviate", "faiss", "elasticsearch",
    "docker", "kubernetes", "aws", "azure", "gcp", "terraform", "ci/cd",
    "github actions", "linux", "git", "pandas", "numpy", "scikit-learn",
    "tensorflow", "pytorch", "keras", "langchain", "openai", "mistral", "llm",
    "rag", "nlp", "machine learning", "deep learning", "computer vision",
    "data science", "data engineering", "spark", "airflow", "kafka", "tableau",
    "power bi", "tailwind", "tailwindcss", "figma", "agile", "scrum",
]

DEGREE_PATTERN = re.compile(
    r"\b(b\.?tech|m\.?tech|b\.?e\.?|m\.?e\.?|b\.?s\.?|m\.?s\.?|b\.?sc|m\.?sc|"
    r"bachelor(?:'s)?|master(?:'s)?|ph\.?d\.?|mba|bca|mca|associate)\b",
    re.IGNORECASE,
)


def extract_json_from_text(raw_text: str) -> Dict[str, Any]:
    """Extract and parse a JSON object from an LLM response safely."""
    if not raw_text:
        return {}
    cleaned = raw_text.strip()

    # Strip markdown code block wrappers properly without str.strip() character bugs
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    # Try direct parse first
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        pass

    # Fall back to finding the outermost {...} object
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(cleaned[start : end + 1])
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            pass

    return {}


def _get_ci(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Case- and separator-insensitive dictionary lookup."""
    normalized_map = {
        re.sub(r"[\s_-]+", "", str(k)).lower(): v for k, v in data.items()
    }
    for key in keys:
        norm_key = re.sub(r"[\s_-]+", "", key).lower()
        if norm_key in normalized_map and normalized_map[norm_key] is not None:
            return normalized_map[norm_key]
    return default


def _ensure_list_of_items(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _ensure_skills(value: Any) -> Dict[str, Any]:
    """Normalize skills into a dictionary of category -> list of strings."""
    if value is None:
        return {}
    if isinstance(value, dict):
        cleaned: Dict[str, Any] = {}
        for k, v in value.items():
            if isinstance(v, list):
                cleaned[str(k)] = [str(item).strip() for item in v if str(item).strip()]
            elif isinstance(v, str) and v.strip():
                cleaned[str(k)] = [s.strip() for s in v.split(",") if s.strip()]
            elif v is not None:
                cleaned[str(k)] = [str(v)]
        return cleaned
    if isinstance(value, list):
        flat = [str(item).strip() for item in value if str(item).strip()]
        return {"Technical Skills": flat} if flat else {}
    if isinstance(value, str) and value.strip():
        flat = [s.strip() for s in value.split(",") if s.strip()]
        return {"Technical Skills": flat} if flat else {}
    return {}


def normalize_resume_data(raw: Dict[str, Any], fallback_name: str = "Unknown Candidate") -> Dict[str, Any]:
    """Normalize LLM or heuristic output into canonical database/API schema keys."""
    name = _get_ci(raw, "Name", "full_name", "candidate_name", default=fallback_name)
    if not name or not str(name).strip():
        name = fallback_name

    email = _get_ci(raw, "Email", "email_address", default=None)
    if isinstance(email, str):
        email = email.strip() or None

    phone = _get_ci(raw, "Phone Number", "Phone", "phone_number", "mobile", default=None)
    if phone is not None:
        phone = str(phone).strip() or None

    skills = _ensure_skills(_get_ci(raw, "Skills", "technical_skills", default={}))
    work_experience = _ensure_list_of_items(
        _get_ci(raw, "Work Experience", "Experience", "employment", default=[])
    )
    education = _ensure_list_of_items(_get_ci(raw, "Education", "academics", default=[]))
    certifications = _ensure_list_of_items(_get_ci(raw, "Certifications", "certificates", default=[]))
    projects = _ensure_list_of_items(_get_ci(raw, "Projects", default=[]))

    gpa_raw = _get_ci(raw, "Gpa", "GPA", "cgpa", default="0")
    gpa = str(gpa_raw).strip() if gpa_raw not in (None, "") else "0"

    return {
        "name": str(name).strip(),
        "email": email,
        "phone_number": phone,
        "skills": skills,
        "work_experience": work_experience,
        "education": education,
        "certifications": certifications,
        "projects": projects,
        "gpa": gpa,
    }


def parse_gpa(gpa_val: Any) -> Optional[float]:
    """Extract numeric GPA from strings like '3.8', '3.8/4.0', '8.5 CGPA'."""
    if gpa_val is None:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", str(gpa_val))
    if not match:
        return None
    try:
        val = float(match.group(1))
        return val if val > 0 else None
    except ValueError:
        return None


def flatten_to_tokens(value: Any) -> Set[str]:
    """Recursively flatten nested dicts/lists/strings into lowercase search tokens and phrases."""
    tokens: Set[str] = set()
    if value is None:
        return tokens
    if isinstance(value, dict):
        for v in value.values():
            tokens.update(flatten_to_tokens(v))
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            tokens.update(flatten_to_tokens(item))
    else:
        text = str(value).strip().lower()
        if text:
            tokens.add(text)
            for word in re.findall(r"[a-z0-9+#.]{2,}", text):
                tokens.add(word)
    return tokens


def _split_sections(text: str) -> Dict[str, List[str]]:
    """Split raw resume text into approximate section buckets."""
    section_headers = {
        "experience": re.compile(r"^(work\s+experience|experience|employment|professional\s+experience)\b", re.I),
        "education": re.compile(r"^(education|academic|qualifications)\b", re.I),
        "skills": re.compile(r"^(skills|technical\s+skills|core\s+competencies|technologies)\b", re.I),
        "projects": re.compile(r"^(projects|key\s+projects|personal\s+projects)\b", re.I),
        "certifications": re.compile(r"^(certifications|certificates|licenses)\b", re.I),
    }

    sections: Dict[str, List[str]] = {
        "header": [],
        "experience": [],
        "education": [],
        "skills": [],
        "projects": [],
        "certifications": [],
    }
    current = "header"

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        matched_section = None
        if len(line) <= 45:
            for key, pattern in section_headers.items():
                if pattern.match(line.rstrip(":")):
                    matched_section = key
                    break
        if matched_section:
            current = matched_section
            continue
        sections[current].append(line)

    return sections


def heuristic_parse_resume(text: str, filename: str = "") -> Dict[str, Any]:
    """Local deterministic resume parser fallback when external LLM keys are not set."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    sections = _split_sections(text)

    email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    email = email_match.group(0) if email_match else None

    phone_match = re.search(
        r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}",
        text,
    )
    phone = phone_match.group(0).strip() if phone_match else None

    gpa_match = re.search(r"(?:gpa|cgpa)\s*[:\-]?\s*(\d(?:\.\d{1,2})?(?:\s*/\s*\d+(?:\.\d+)?)?)", text, re.I)
    gpa = gpa_match.group(1) if gpa_match else "0"

    # Infer name from first non-contact header line
    fallback_stem = re.sub(r"[_-]+", " ", filename.rsplit(".", 1)[0]).strip() if filename else "Candidate"
    name = fallback_stem or "Candidate"
    for line in (sections["header"] or lines)[:4]:
        if "@" in line or re.search(r"\d{4,}", line) or "http" in line.lower():
            continue
        if 2 <= len(line.split()) <= 5 and len(line) <= 50:
            name = line
            break

    # Extract skills from dictionary match + skills section lines
    lower_text = text.lower()
    detected_skills: List[str] = []
    for skill in KNOWN_SKILLS:
        escaped = re.escape(skill)
        if re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", lower_text):
            detected_skills.append(skill.upper() if len(skill) <= 3 and skill not in ("r", "go") else skill.title())

    for skill_line in sections["skills"]:
        cleaned_line = re.sub(r"^[A-Za-z\s&/]+:\s*", "", skill_line)
        for token in re.split(r"[,|•·/]+", cleaned_line):
            tok = token.strip()
            if 1 < len(tok) <= 35 and tok.lower() not in {s.lower() for s in detected_skills}:
                detected_skills.append(tok)

    # Extract education entries
    education_entries: List[Dict[str, str]] = []
    edu_lines = sections["education"] or [ln for ln in lines if DEGREE_PATTERN.search(ln)]
    if edu_lines:
        for i in range(0, min(len(edu_lines), 6), 2):
            chunk = edu_lines[i : i + 2]
            year_match = re.search(r"(19|20)\d{2}(?:\s*[-–]\s*(?:(19|20)\d{2}|present))?", " ".join(chunk), re.I)
            education_entries.append({
                "Degree": chunk[0],
                "Institution": chunk[1] if len(chunk) > 1 else "",
                "Year": year_match.group(0) if year_match else "",
            })

    # Extract work experience entries
    experience_entries: List[Dict[str, str]] = []
    exp_lines = sections["experience"]
    if exp_lines:
        current_entry: List[str] = []
        for ln in exp_lines[:24]:
            has_dates = bool(re.search(r"(19|20)\d{2}|present", ln, re.I))
            if has_dates and current_entry:
                experience_entries.append({
                    "Role": current_entry[0],
                    "Details": " ".join(current_entry[1:]) if len(current_entry) > 1 else "",
                })
                current_entry = [ln]
            else:
                current_entry.append(ln)
        if current_entry:
            experience_entries.append({
                "Role": current_entry[0],
                "Details": " ".join(current_entry[1:]) if len(current_entry) > 1 else "",
            })

    # Extract projects
    project_entries: List[Dict[str, str]] = []
    for ln in sections["projects"][:8]:
        if ":" in ln:
            title, desc = ln.split(":", 1)
            project_entries.append({"Name": title.strip(), "Description": desc.strip()})
        else:
            project_entries.append({"Name": ln[:60], "Description": ln})

    # Extract certifications
    cert_entries = [{"Name": ln} for ln in sections["certifications"][:8]]

    return normalize_resume_data(
        {
            "Name": name,
            "Email": email,
            "Phone Number": phone,
            "Skills": {"Extracted Skills": detected_skills[:30]},
            "Work Experience": experience_entries[:6],
            "Education": education_entries[:4],
            "Certifications": cert_entries,
            "Projects": project_entries[:6],
            "Gpa": gpa,
        },
        fallback_name=name,
    )


def heuristic_parse_query(description: str) -> Dict[str, Any]:
    """Extract structured search criteria from a recruiter prompt locally without an LLM."""
    lower = description.lower()
    skills = [
        skill for skill in KNOWN_SKILLS
        if re.search(rf"(?<![a-z0-9]){re.escape(skill)}(?![a-z0-9])", lower)
    ]

    gpa_match = re.search(r"(?:gpa|cgpa)\s*(?:>=|>|of|above|min(?:imum)?)?\s*(\d(?:\.\d{1,2})?)", lower)
    gpa = gpa_match.group(1) if gpa_match else "0"

    degree_matches = DEGREE_PATTERN.findall(description)
    words = [w for w in re.findall(r"[a-zA-Z0-9+#.]{3,}", lower) if w not in {
        "with", "and", "for", "the", "looking", "candidate", "developer", "engineer",
        "experience", "years", "year", "plus", "minimum", "strong", "skills", "background",
        "who", "has", "have", "that", "from", "into", "using",
    }]

    return {
        "skills": list(dict.fromkeys(skills or words[:8])),
        "work_experience": words[:10],
        "education": list(dict.fromkeys([d.lower() for d in degree_matches])),
        "certifications": [],
        "projects": words[:8],
        "gpa": gpa,
    }
