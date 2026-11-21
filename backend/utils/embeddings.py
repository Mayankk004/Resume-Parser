"""Gemini 768-dim L2-normalized embeddings via the official google-genai SDK."""

import math
import os
from typing import List
from google import genai
from google.genai import types

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 768


def _get_genai_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")
    return genai.Client(api_key=api_key)


def l2_normalize(vector: List[float]) -> List[float]:
    """Manually L2-normalize an embedding vector using pure Python math."""
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0.0:
        return vector
    return [x / norm for x in vector]


def generate_embedding(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> List[float]:
    """Generate a 768-dim L2-normalized embedding using gemini-embedding-001."""
    client = _get_genai_client()
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=EMBEDDING_DIM,
        ),
    )
    values = list(response.embeddings[0].values)
    return l2_normalize(values)


def generate_document_embedding(text: str) -> List[float]:
    """Generate a RETRIEVAL_DOCUMENT embedding for a resume."""
    return generate_embedding(text, task_type="RETRIEVAL_DOCUMENT")


def generate_query_embedding(query: str) -> List[float]:
    """Generate a RETRIEVAL_QUERY embedding for a recruiter search prompt."""
    return generate_embedding(query, task_type="RETRIEVAL_QUERY")
