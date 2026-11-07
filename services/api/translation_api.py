"""Provider-backed translation API for ORIOM7.

The provider endpoint is configured by operators, never supplied by callers.
Only HTTPS endpoints are accepted outside local development.
"""
from __future__ import annotations

import os
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from commercial_api import record_usage, require_api_key

router = APIRouter(tags=["translation"])

class TranslationRequest(BaseModel):
    text: str = Field(min_length=1, max_length=50000)
    source: str = Field(default="auto", min_length=2, max_length=35)
    target: str = Field(min_length=2, max_length=35)
    format: str = Field(default="text", pattern="^(text|html)$")

class TranslationProvider:
    def __init__(self, endpoint: str, api_key: str | None, timeout: float = 20.0):
        parsed = urlparse(endpoint)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("Translation endpoint must be a trusted HTTPS URL")
        self.endpoint = endpoint
        self.api_key = api_key
        self.timeout = timeout

    async def translate(self, text: str, source: str, target: str, text_format: str) -> str:
        payload = {"q": text, "source": source, "target": target, "format": text_format}
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            payload["api_key"] = self.api_key
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False) as client:
            response = await client.post(self.endpoint, json=payload, headers=headers)
            response.raise_for_status()
        data = response.json()
        translated = data.get("translatedText") if isinstance(data, dict) else None
        if not isinstance(translated, str) or not translated.strip():
            raise ValueError("Translation provider returned an invalid response")
        return translated

def build_translation_provider_from_env() -> TranslationProvider | None:
    endpoint = os.getenv("ORIOM7_TRANSLATION_ENDPOINT")
    if not endpoint:
        return None
    return TranslationProvider(endpoint, os.getenv("ORIOM7_TRANSLATION_API_KEY"))

@router.post("/v1/translation/text")
async def translate_text(
    body: TranslationRequest,
    request: Request,
    key: dict = Depends(require_api_key),
):
    provider = getattr(request.app.state, "translation_provider", None)
    if provider is None:
        raise HTTPException(status_code=503, detail="Translation provider is not configured")
    if body.source.lower() == body.target.lower():
        raise HTTPException(status_code=422, detail="Source and target languages must differ")
    try:
        translated = await provider.translate(body.text, body.source, body.target, body.format)
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Translation provider timed out") from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail="Translation provider rejected the request") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Translation provider failed or returned an invalid response") from exc
    await record_usage(
        request, key, "translation", len(body.text), 200,
        {"source": body.source, "target": body.target, "format": body.format},
    )
    return {
        "object": "translation",
        "source_language": body.source,
        "target_language": body.target,
        "translated_text": translated,
        "usage": {"input_characters": len(body.text)},
    }
