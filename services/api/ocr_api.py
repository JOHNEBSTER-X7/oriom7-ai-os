"""Provider-backed OCR and document text extraction.

Uploads are held in memory for the request, size/type checked, and forwarded
only to an operator-configured HTTPS provider. ORIOM7 does not persist files.
"""
from __future__ import annotations

import hashlib
import json
import os
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from commercial_api import record_usage, require_api_key

router = APIRouter(tags=["document-intelligence"])

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_PROVIDER_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_PAGES = 100
ALLOWED_TYPES = {
    "application/pdf": (b"%PDF-",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/tiff": (b"II*\x00", b"MM\x00*"),
}

class OCRProvider:
    def __init__(self, endpoint: str, api_key: str | None, timeout: float = 45.0):
        parsed = urlparse(endpoint)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("OCR endpoint must be a trusted HTTPS URL")
        self.endpoint = endpoint
        self.api_key = api_key
        self.timeout = timeout

    async def extract(self, content: bytes, filename: str, media_type: str, language: str):
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        files = {"file": (filename, content, media_type)}
        data = {"language": language}
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False) as client:
            async with client.stream("POST", self.endpoint, headers=headers, files=files, data=data) as response:
                response.raise_for_status()
                chunks: list[bytes] = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > MAX_PROVIDER_RESPONSE_BYTES:
                        raise ValueError("OCR provider response exceeded the configured limit")
                    chunks.append(chunk)
        payload = json.loads(b"".join(chunks).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("OCR provider response must be a JSON object")
        text = payload.get("text")
        pages = payload.get("pages", 1)
        if not isinstance(text, str) or not text.strip() or len(text) > 1_000_000:
            raise ValueError("OCR provider returned invalid extracted text")
        if isinstance(pages, bool) or not isinstance(pages, int) or not 1 <= pages <= MAX_PAGES:
            raise ValueError("OCR provider returned an invalid page count")
        return text, pages

def build_ocr_provider_from_env() -> OCRProvider | None:
    endpoint = os.getenv("ORIOM7_OCR_ENDPOINT")
    if not endpoint:
        return None
    return OCRProvider(endpoint, os.getenv("ORIOM7_OCR_API_KEY"))

def validate_upload(content: bytes, media_type: str) -> None:
    signatures = ALLOWED_TYPES.get(media_type)
    if signatures is None or not any(content.startswith(signature) for signature in signatures):
        raise HTTPException(status_code=415, detail="Only valid PDF, PNG, JPEG and TIFF documents are supported")
    if not content:
        raise HTTPException(status_code=422, detail="Uploaded document is empty")

@router.post("/v1/documents/ocr")
async def extract_document_text(
    request: Request,
    file: UploadFile = File(...),
    language: str = Form(default="auto", min_length=2, max_length=35),
    key: dict = Depends(require_api_key),
):
    provider = getattr(request.app.state, "ocr_provider", None)
    if provider is None:
        raise HTTPException(status_code=503, detail="OCR provider is not configured")
    media_type = (file.content_type or "").split(";", 1)[0].strip().lower()
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Document exceeds the 15 MB upload limit")
    validate_upload(content, media_type)
    digest = hashlib.sha256(content).hexdigest()
    safe_filename = "document" + {
        "application/pdf": ".pdf",
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/tiff": ".tiff",
    }[media_type]
    try:
        extracted_text, pages = await provider.extract(content, safe_filename, media_type, language)
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="OCR provider timed out") from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail="OCR provider rejected the document") from exc
    except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail="OCR provider failed or returned an invalid response") from exc
    await record_usage(
        request, key, "ocr", pages, 200,
        {"media_type": media_type, "sha256": digest, "language": language},
    )
    return {
        "object": "document_extraction",
        "filename": safe_filename,
        "media_type": media_type,
        "sha256": digest,
        "language": language,
        "pages": pages,
        "extracted_text": extracted_text,
        "usage": {"pages": pages},
        "storage": "not_persisted",
    }
