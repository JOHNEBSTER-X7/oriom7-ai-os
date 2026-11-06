"""Owner-scoped image embedding and similarity search (no image-byte persistence).

The configured visual embedding provider receives image bytes transiently. ORIOM7
stores only the vector, caller-supplied label, content hash and ownership metadata.
"""
from __future__ import annotations

import base64
import hashlib
import math
import os
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from commercial_api import record_usage, require_api_key
from vision_api import MAX_IMAGE_BYTES, validate_image

router = APIRouter(tags=["visual-search"])


class VisualEmbeddingProvider:
    def __init__(self, endpoint: str, api_key: str | None, model: str, dimensions: int, timeout: float = 45.0):
        parsed = urlparse(endpoint)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("Visual embedding endpoint must be a trusted HTTPS URL")
        if not 1 <= dimensions <= 16000:
            raise ValueError("Visual embedding dimensions must be between 1 and 16000")
        self.endpoint, self.api_key, self.model = endpoint, api_key, model
        self.dimensions, self.timeout = dimensions, timeout

    async def embed(self, content: bytes, media_type: str) -> list[float]:
        payload = {"model": self.model, "image": {
            "media_type": media_type,
            "data_base64": base64.b64encode(content).decode("ascii"),
        }}
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False) as client:
            response = await client.post(self.endpoint, json=payload, headers=headers)
            response.raise_for_status()
        data = response.json()
        vector = data.get("embedding") if isinstance(data, dict) else None
        if (not isinstance(vector, list) or len(vector) != self.dimensions
            or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in vector)):
            raise ValueError("Visual embedding provider returned an invalid vector")
        return [float(v) for v in vector]


def build_visual_embedding_provider_from_env():
    endpoint = os.getenv("ORIOM7_VISUAL_EMBEDDING_ENDPOINT")
    if not endpoint:
        return None
    try:
        dimensions = int(os.getenv("ORIOM7_VISUAL_EMBEDDING_DIMENSIONS", "1024"))
    except ValueError as exc:
        raise RuntimeError("ORIOM7_VISUAL_EMBEDDING_DIMENSIONS must be an integer") from exc
    return VisualEmbeddingProvider(
        endpoint, os.getenv("ORIOM7_VISUAL_EMBEDDING_API_KEY"),
        os.getenv("ORIOM7_VISUAL_EMBEDDING_MODEL", "default"), dimensions,
    )


def _pool(request: Request):
    pool = getattr(request.app.state, "database_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="Visual search database is not configured")
    return pool


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


async def _embed(request: Request, content: bytes, media_type: str) -> tuple[list[float], str]:
    provider = getattr(request.app.state, "visual_embedding_provider", None)
    if provider is None:
        raise HTTPException(status_code=503, detail="Visual embedding provider is not configured")
    try:
        return await provider.embed(content, media_type), provider.model
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Visual embedding provider timed out") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Visual embedding provider failed or returned an invalid vector") from exc


@router.post("/v1/vision/index", status_code=201)
async def index_visual_item(
    request: Request,
    file: UploadFile = File(...),
    label: str = Form(..., min_length=1, max_length=240),
    media_type: str = Form(default="image/jpeg"),
    key: dict = Depends(require_api_key),
):
    content = await file.read(MAX_IMAGE_BYTES + 1)
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds the 10 MB upload limit")
    media_type = (file.content_type or media_type).split(";", 1)[0].strip().lower()
    validate_image(content, media_type)
    vector, model = await _embed(request, content, media_type)
    digest = hashlib.sha256(content).hexdigest()
    pool = _pool(request)
    async with pool.acquire() as connection:
        row = await connection.fetchrow(
            """INSERT INTO visual_search_items
               (owner_id, label, content_sha256, embedding_model, embedding_dimensions, embedding)
               VALUES ($1, $2, $3, $4, $5, $6::vector)
               RETURNING visual_item_id::text, created_at""",
            key["owner_id"], label.strip(), digest, model, len(vector), _vector_literal(vector),
        )
    await record_usage(request, key, "visual_search", 1, 201, {"operation": "index", "sha256": digest})
    return {"id": row["visual_item_id"], "label": label.strip(), "sha256": digest,
            "created_at": row["created_at"].isoformat(), "storage": "embedding_only",
            "raw_image_persisted": False}


@router.post("/v1/vision/search")
async def search_visual_items(
    request: Request,
    file: UploadFile = File(...),
    limit: int = Form(default=10, ge=1, le=50),
    key: dict = Depends(require_api_key),
):
    content = await file.read(MAX_IMAGE_BYTES + 1)
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds the 10 MB upload limit")
    media_type = (file.content_type or "").split(";", 1)[0].strip().lower()
    validate_image(content, media_type)
    vector, model = await _embed(request, content, media_type)
    pool = _pool(request)
    async with pool.acquire() as connection:
        rows = await connection.fetch(
            """SELECT visual_item_id::text AS id, label, content_sha256 AS sha256,
                      1 - (embedding <=> $1::vector) AS similarity
               FROM visual_search_items
               WHERE owner_id=$2 AND embedding_model=$3 AND embedding_dimensions=$4
               ORDER BY embedding <=> $1::vector LIMIT $5""",
            _vector_literal(vector), key["owner_id"], model, len(vector), limit,
        )
    await record_usage(request, key, "visual_search", 1, 200, {"operation": "search"})
    return {"object": "visual_similarity_results", "model": model,
            "results": [{"id": r["id"], "label": r["label"], "sha256": r["sha256"],
                         "similarity": float(r["similarity"])} for r in rows],
            "raw_query_image_persisted": False, "usage": {"images": 1}}


@router.delete("/v1/vision/index/{item_id}", status_code=204)
async def delete_visual_item(item_id: str, request: Request, key: dict = Depends(require_api_key)):
    pool = _pool(request)
    async with pool.acquire() as connection:
        result = await connection.execute(
            "DELETE FROM visual_search_items WHERE visual_item_id=$1::uuid AND owner_id=$2",
            item_id, key["owner_id"],
        )
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Visual index item not found")
