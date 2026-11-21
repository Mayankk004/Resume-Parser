"""Neon Realtime capability query sealing helper (Compact JWE A256GCM v2)."""

import base64
import hashlib
import json
import os
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SECRET_PREFIX = "nrt_live_1"
SEALED_QUERY_LIFETIME_SECONDS = 60
FINGERPRINT_DOMAIN = b"neon-live-query-fingerprint-v1\x00"


def is_realtime_configured() -> bool:
    return bool(
        os.getenv("NEON_REALTIME_URL", "").strip()
        and os.getenv("NEON_REALTIME_SECRET", "").strip()
        and os.getenv("DATABASE_URL", "").strip()
    )


def get_database_name() -> str:
    raw = os.getenv("DATABASE_URL", "").strip()
    if not raw:
        return "neondb"
    parsed = urlparse(raw)
    name = parsed.path.lstrip("/").split("?")[0]
    return name or "neondb"


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(val: str) -> bytes:
    padding = "=" * ((4 - len(val) % 4) % 4)
    return base64.urlsafe_b64decode((val + padding).encode("ascii"))


def _parse_secret(secret: str) -> bytes:
    if not secret.startswith(SECRET_PREFIX):
        raise ValueError("Invalid NEON_REALTIME_SECRET prefix")
    key = _b64url_decode(secret[len(SECRET_PREFIX):])
    if len(key) != 32:
        raise ValueError("Invalid NEON_REALTIME_SECRET key length")
    return key


def _query_fingerprint(sql: str, parameters: List[Dict[str, Any]]) -> str:
    canonical = json.dumps(
        {"sql": sql, "parameters": parameters},
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(FINGERPRINT_DOMAIN + canonical).hexdigest()


def seal_live_query(
    sql: str,
    parameters: Optional[List[Dict[str, Any]]] = None,
    debug_mode: bool = False,
) -> Dict[str, Any]:
    """Seal a read-only SQL query into a Neon Realtime v2 Compact-JWE capability."""
    secret = os.getenv("NEON_REALTIME_SECRET", "").strip()
    if not secret:
        raise ValueError("NEON_REALTIME_SECRET is not configured.")

    key = _parse_secret(secret)
    db_name = get_database_name()
    encoded_params = parameters or []
    fingerprint = _query_fingerprint(sql, encoded_params)

    issued_at = int(time.time())
    expires_at = issued_at + SEALED_QUERY_LIFETIME_SECONDS

    claims = {
        "v": 2,
        "aud": "realtime-proxy",
        "database": db_name,
        "error_details": "full" if debug_mode else "safe",
        "issuer": {
            "sdk": "javascript",
            "release_line": "0.2",
            "query_source": "raw_sql",
        },
        "query_fingerprint": fingerprint,
        "sql": sql,
        "parameters": encoded_params,
        "iat": issued_at,
        "exp": expires_at,
    }
    header = {"alg": "dir", "enc": "A256GCM", "v": 2}

    encoded_header = _b64url_encode(
        json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )
    claims_bytes = json.dumps(claims, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    iv = os.urandom(12)
    encrypted = AESGCM(key).encrypt(iv, claims_bytes, encoded_header.encode("ascii"))
    ciphertext, tag = encrypted[:-16], encrypted[-16:]

    capability = ".".join([
        encoded_header,
        "",
        _b64url_encode(iv),
        _b64url_encode(ciphertext),
        _b64url_encode(tag),
    ])

    return {
        "capability": capability,
        "queryFingerprint": fingerprint,
        "expiresAt": expires_at * 1000,
    }
