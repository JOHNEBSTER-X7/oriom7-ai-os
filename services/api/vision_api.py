"""Provider-backed visual question answering for ORIOM7.

Images are bounded and held in memory for the request. The configured HTTPS
provider receives the image and question; ORIOM7 does not persist image bytes.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from commercial_api import record_usage, require_api_key

router = APIRouter(tags=["visual-intelligence"])

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_PROVIDER_RESPONSE_BYTES = 1 * 1024 * 1024
MAX_QUESTION_CHARS = 2000
MAX_DESCRIPTION_CHARS = 100_000
ALLOWED_TYPES = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/webp": (b"RIFF",),
}


class VisualIntelligenceProvider:
    """Adapter for an operator-configured ORIOM7 vision JSON endpoint.

    Request JSON: {model, question, image: {media_type, data_base64}}
    Response JSON: {description, answer?, objects?, text_found?}
    """

    def __init__(self, endpoint: str, api_key: str | None, model: str = "default", timeout: float = 60.0):
        parsed = urlparse(endpoint)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("Visual intelligence endpoint must be a trusted HTTPS URL")
        self.endpoint = endpoint
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    async def analyze(self, content: bytes, media_type: str, question: str) -> dict:
        payload = {
            "model": self.model,
            "question": question,
            "image": {
                "media_type": media_type,
                "data_base64": base64.b64encode(content).decode("ascii"),
            },
        }
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False) as client:
            async with client.stream("POST", self.endpoint, headers=headers, json=payload) as response:
                response.raise_for_status()
                chunks: list[bytes] = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > MAX_PROVIDER_RESPONSE_BYTES:
                        raise ValueError("Visual provider response exceeded the configured limit")
                    chunks.append(chunk)
        data = json.loads(b"".join(chunks).decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Visual provider response must be a JSON object")
        description = data.get("description")
        if not isinstance(description, str) or not description.strip() or len(description) > MAX_DESCRIPTION_CHARS:
            raise ValueError("Visual provider returned an invalid description")
        answer = data.get("answer")
        if answer is not None and (not isinstance(answer, str) or len(answer) > MAX_DESCRIPTION_CHARS):
            raise ValueError("Visual provider returned an invalid answer")
        objects = data.get("objects", [])
        if not isinstance(objects, list) or len(objects) > 100:
            raise ValueError("Visual provider returned invalid objects")
        clean_objects = []
        for item in objects:
            if not isinstance(item, str) or not item.strip() or len(item) > 160:
                raise ValueError("Visual provider returned an invalid object label")
            clean_objects.append(item)
        text_found = data.get("text_found", [])
        if not isinstance(text_found, list) or len(text_found) > 100:
            raise ValueError("Visual provider returned invalid detected text")
        clean_text = []
        for item in text_found:
            if not isinstance(item, str) or len(item) > 2000:
                raise ValueError("Visual provider returned invalid detected text")
            clean_text.append(item)
        return {
            "description": description.strip(),
            "answer": answer.strip() if isinstance(answer, str) else None,
            "objects": clean_objects,
            "text_found": clean_text,
        }


def build_visual_provider_from_env() -> VisualIntelligenceProvider | None:
    endpoint = os.getenv("ORIOM7_VISION_ENDPOINT")
    if not endpoint:
        return None
    return VisualIntelligenceProvider(
        endpoint,
        os.getenv("ORIOM7_VISION_API_KEY"),
        os.getenv("ORIOM7_VISION_MODEL", "default"),
    )


def validate_image(content: bytes, media_type: str) -> None:
    signatures = ALLOWED_TYPES.get(media_type)
    if not content:
        raise HTTPException(status_code=422, detail="Uploaded image is empty")
    if signatures is None:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG and WebP images are supported")
    if not any(content.startswith(signature) for signature in signatures):
        raise HTTPException(status_code=415, detail="Image file signature does not match its media type")
    if media_type == "image/webp" and content[8:12] != b"WEBP":
        raise HTTPException(status_code=415, detail="Invalid WebP image signature")


@router.post("/v1/vision/analyze")
async def analyze_image(
    request: Request,
    file: UploadFile = File(...),
    question: str = Form(default="Describe this image clearly.", min_length=1, max_length=MAX_QUESTION_CHARS),
    key: dict = Depends(require_api_key),
):
    provider = getattr(request.app.state, "vision_provider", None)
    if provider is None:
        raise HTTPException(status_code=503, detail="Visual intelligence provider is not configured")
    media_type = (file.content_type or "").split(";", 1)[0].strip().lower()
    content = await file.read(MAX_IMAGE_BYTES + 1)
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds the 10 MB upload limit")
    validate_image(content, media_type)
    digest = hashlib.sha256(content).hexdigest()
    try:
        result = await provider.analyze(content, media_type, question.strip())
        if not isinstance(result, dict):
            raise ValueError("Visual provider returned an invalid result")
        description = result.get("description")
        answer = result.get("answer")
        objects = result.get("objects", [])
        text_found = result.get("text_found", [])
        if not isinstance(description, str) or not description.strip() or len(description) > MAX_DESCRIPTION_CHARS:
            raise ValueError("Visual provider returned an invalid description")
        if answer is not None and (not isinstance(answer, str) or len(answer) > MAX_DESCRIPTION_CHARS):
            raise ValueError("Visual provider returned an invalid answer")
        if (not isinstance(objects, list) or len(objects) > 100
            or any(not isinstance(item, str) or not item.strip() or len(item) > 160 for item in objects)):
            raise ValueError("Visual provider returned invalid objects")
        if (not isinstance(text_found, list) or len(text_found) > 100
            or any(not isinstance(item, str) or len(item) > 2000 for item in text_found)):
            raise ValueError("Visual provider returned invalid detected text")
        result = {
            "description": description.strip(),
            "answer": answer.strip() if isinstance(answer, str) else None,
            "objects": objects,
            "text_found": text_found,
        }
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Visual intelligence provider timed out") from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail="Visual intelligence provider rejected the image") from exc
    except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail="Visual intelligence provider failed or returned invalid data") from exc
    await record_usage(
        request, key, "vision", 1, 200,
        {"media_type": media_type, "sha256": digest, "question_characters": len(question)},
    )
    return {
        "object": "visual_analysis",
        "media_type": media_type,
        "sha256": digest,
        "question": question.strip(),
        **result,
        "usage": {"images": 1},
        "storage": "not_persisted",
    }
