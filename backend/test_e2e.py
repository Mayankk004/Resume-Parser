"""End-to-end verification tests for Neon Postgres/pgvector, Neon Object Storage, Neon Realtime, and Gemini."""

import os
import sys
import urllib.request
from fastapi.testclient import TestClient

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from main import app  # noqa: E402


def _make_minimal_pdf_bytes(lines: list[str]) -> bytes:
    """Construct a valid single-page PDF in memory."""
    escaped = [
        line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        for line in lines
    ]
    text_ops = ["BT", "/F1 11 Tf", "50 760 Td", "15 TL"]
    for idx, line in enumerate(escaped):
        if idx == 0:
            text_ops.append(f"({line}) Tj")
        else:
            text_ops.append(f"T* ({line}) Tj")
    text_ops.append("ET")
    stream = "\n".join(text_ops).encode("latin-1", errors="replace")

    objs = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n",
        f"4 0 obj << /Length {len(stream)} >> stream\n".encode("ascii") + stream + b"\nendstream endobj\n",
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objs:
        offsets.append(len(pdf))
        pdf.extend(obj)

    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode("ascii"))
    for off in offsets[1:]:
        pdf.extend(f"{off:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


def run_tests() -> None:
    with TestClient(app) as client:
        # 1. Health & config status
        r_health = client.get("/health")
        assert r_health.status_code == 200, r_health.text
        health = r_health.json()
        print("[OK] Health:", health)
        assert health["database"] == "connected"

        r_cfg = client.get("/api/v1/config/status")
        assert r_cfg.status_code == 200, r_cfg.text
        cfg = r_cfg.json()
        print("[OK] Config Status:", cfg)
        assert cfg["gemini_configured"] is True
        assert cfg["database"] == "postgresql"
        assert cfg["storage_configured"] is True
        assert cfg["realtime_configured"] is True

        # 2. Validate upload guard (reject non-PDF)
        bad_resp = client.post(
            "/api/v1/resume/",
            files=[("files", ("notes.txt", b"not a pdf", "text/plain"))],
        )
        assert bad_resp.status_code == 400, bad_resp.text

        # 3. Batch upload 2 in-memory PDF resumes (Gemini parse + Neon Object Storage + pgvector)
        pdf1 = _make_minimal_pdf_bytes([
            "Alice Johnson",
            "alice.johnson.neon@example.com | +1-555-234-5678",
            "Skills: Python, FastAPI, PostgreSQL, Docker, AWS",
            "Work Experience: Senior Backend Engineer at Acme Cloud (2022 - Present)",
            "Built Python FastAPI microservices with PostgreSQL and Docker.",
            "Education: B.S. Computer Science, State University (2022) GPA: 3.85",
        ])
        pdf2 = _make_minimal_pdf_bytes([
            "Bob Martinez",
            "bob.martinez.neon@example.com | +1-555-987-6543",
            "Skills: React, TypeScript, Next.js, Tailwind CSS, Node.js",
            "Work Experience: Frontend Engineer at PixelWeb (2021 - Present)",
            "Built responsive web interfaces using React and TypeScript.",
            "Education: B.S. Software Engineering, Tech Institute (2021) GPA: 3.6",
        ])

        up_resp = client.post(
            "/api/v1/resume/",
            files=[
                ("files", ("alice_backend.pdf", pdf1, "application/pdf")),
                ("files", ("bob_frontend.pdf", pdf2, "application/pdf")),
            ],
        )
        assert up_resp.status_code == 200, up_resp.text
        batch_id = up_resp.json()["batch_id"]

        status_resp = client.get(f"/api/v1/resume/batch/{batch_id}")
        assert status_resp.status_code == 200, status_resp.text
        statuses = status_resp.json()["files"]
        print("[OK] Batch Upload Status:", statuses)
        assert all(item["status"] == "completed" for item in statuses), statuses
        ids = [item["resume_id"] for item in statuses]

        # 4. Verify Neon Object Storage presigned download URL actually serves the PDF
        r_detail = client.get(f"/api/v1/resume/{ids[0]}")
        assert r_detail.status_code == 200, r_detail.text
        detail = r_detail.json()
        assert detail["storage_key"], "Expected storage_key to be populated"
        assert detail["pdf_url"], "Expected presigned pdf_url to be generated"
        with urllib.request.urlopen(detail["pdf_url"], timeout=15) as dl:
            downloaded_bytes = dl.read()
            assert dl.status == 200
            assert downloaded_bytes.startswith(b"%PDF-1.4")
        print(f"[OK] Neon Object Storage verified: uploaded & downloaded {len(downloaded_bytes)} bytes via presigned URL ({detail['storage_key']})")

        # 5. Verify Neon Realtime sealed capability endpoint
        r_live = client.post("/api/v1/resumes/live")
        assert r_live.status_code == 200, r_live.text
        live_payload = r_live.json()
        assert live_payload["realtimeUrl"].startswith("wss://")
        assert len(live_payload["sealedQuery"]["capability"].split(".")) == 5
        print("[OK] Neon Realtime sealed query issued:", live_payload["sealedQuery"]["queryFingerprint"][:16] + "...")

        # 6. Hybrid pgvector + Gemini search
        search_resp = client.post(
            "/api/v1/search-resume/",
            json={"user_prompt": "Python FastAPI backend developer with PostgreSQL and Docker", "top_k": 5},
        )
        assert search_resp.status_code == 200, search_resp.text
        search_data = search_resp.json()
        assert len(search_data["results"]) >= 2, search_data
        top = search_data["results"][0]
        print(
            "[OK] pgvector Hybrid Search top candidate:",
            top["resume"]["name"],
            "| Match:",
            top["match_score"],
            "| Semantic:",
            top["semantic_score"],
            "| Matched skills:",
            top["matched_skills"],
        )
        assert top["resume"]["name"] == "Alice Johnson"

        # 7. Clean up test records + Object Storage objects
        for rid in ids:
            del_resp = client.delete(f"/api/v1/resume/{rid}")
            assert del_resp.status_code == 200, del_resp.text
        print("[OK] Cleanup succeeded (Postgres + Object Storage). All E2E checks passed!")


if __name__ == "__main__":
    run_tests()
