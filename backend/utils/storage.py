"""Neon Object Storage (S3-compatible) helper using boto3 with path-style SigV4 addressing."""

import os
import re
import uuid
from typing import Optional

import boto3
from botocore.config import Config


def is_storage_configured() -> bool:
    return all(
        os.getenv(var, "").strip()
        for var in (
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_ENDPOINT_URL_S3",
            "AWS_REGION",
        )
    )


def get_bucket_name() -> str:
    return os.getenv("NEON_STORAGE_BUCKET", "assets").strip() or "assets"


def _get_s3_client():
    if not is_storage_configured():
        return None
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("AWS_ENDPOINT_URL_S3", "").strip(),
        region_name=os.getenv("AWS_REGION", "us-east-2").strip(),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "").strip(),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "").strip(),
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    )


def upload_pdf_to_storage(pdf_bytes: bytes, file_name: str) -> Optional[str]:
    """Upload PDF bytes to Neon Object Storage and return the stored object key."""
    client = _get_s3_client()
    if client is None:
        return None

    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(file_name or "resume.pdf"))
    object_key = f"resumes/{uuid.uuid4().hex[:12]}_{safe_name}"
    bucket = get_bucket_name()

    client.put_object(
        Bucket=bucket,
        Key=object_key,
        Body=pdf_bytes,
        ContentType="application/pdf",
    )
    return object_key


def get_presigned_pdf_url(object_key: Optional[str], expires_in: int = 3600) -> Optional[str]:
    """Generate a short-lived presigned GET URL for a stored resume PDF."""
    if not object_key:
        return None
    client = _get_s3_client()
    if client is None:
        return None

    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": get_bucket_name(), "Key": object_key},
        ExpiresIn=expires_in,
    )


def delete_pdf_from_storage(object_key: Optional[str]) -> None:
    """Remove a stored PDF object from Neon Object Storage if present."""
    if not object_key:
        return
    client = _get_s3_client()
    if client is None:
        return
    try:
        client.delete_object(Bucket=get_bucket_name(), Key=object_key)
    except Exception as exc:
        print(f"[WARN] Failed to delete object '{object_key}' from Neon Storage: {exc}")
