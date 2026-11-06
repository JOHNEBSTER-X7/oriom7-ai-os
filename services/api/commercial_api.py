"""ORIOM7 commercial developer API foundation.

API keys are shown once and stored only as SHA-256 hashes. User identity for key
issuance must be set by trusted authentication middleware (request.state.user_id).
Provider calls are disabled unless their corresponding server-side credentials
are configured. Never expose provider credentials to clients.
"""
from __future__ import annotations

import hashlib
import secrets
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(tags=["developer-platform"])

PRODUCTS = [
    {"code": "translation", "name": "Multilingual Translation API", "status": "planned", "unit": "characters", "description": "Translate and localise authorised text while preserving the source."},
    {"code": "ocr", "name": "OCR & Document Intelligence API", "status": "planned", "unit": "pages", "description": "Extract text and structured fields from customer-authorised documents."},
    {"code": "speech", "name": "Speech & Transcription API", "status": "planned", "unit": "audio_seconds", "description": "Transcribe speech and produce accessible text."},
    {"code": "text_to_speech", "name": "Text-to-Speech API", "status": "planned", "unit": "characters", "description": "Generate spoken output using a configured speech provider."},
    {"code": "embeddings", "name": "Universal Text Embedding API", "status": "preview", "unit": "input_characters", "description": "Create vectors using the configured embedding model; dimensions and model are returned."},
    {"code": "multilingual_search", "name": "Global Multilingual Search API", "status": "existing_core_preview", "unit": "requests", "description": "Hybrid search foundation exists; cross-language quality and commercial controls require further integration."},
]

class CreateKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    plan_code: str = Field(default="starter", pattern="^(starter|builder|business|enterprise)$")

class EmbeddingRequest(BaseModel):
    input: str | list[str] = Field(min_length=1)
    model: str | None = Field(default=None, max_length=120)

async def _database(request: Request):
    pool = getattr(request.app.state, "database_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="Developer API persistence is not configured")
    return pool

async def require_api_key(request: Request, authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="A valid ORIOM7 developer API key is required")
    token = authorization[7:].strip()
    if not token.startswith("oriom_live_") or len(token) < 32:
        raise HTTPException(status_code=401, detail="Invalid developer API key")
    pool = await _database(request)
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    async with pool.acquire() as connection:
        row = await connection.fetchrow(
            """UPDATE developer_api_keys SET last_used_at=NOW()
               WHERE key_hash=$1 AND revoked_at IS NULL
               RETURNING api_key_id::text, owner_id, plan_code""",
            digest,
        )
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid or revoked developer API key")
    request.state.developer_key = dict(row)
    return dict(row)

async def record_usage(request: Request, key: dict, product: str, units: int, status: int, metadata: dict | None = None):
    pool = await _database(request)
    async with pool.acquire() as connection:
        await connection.execute(
            """INSERT INTO developer_api_usage
               (api_key_id, product_code, units, status_code, metadata)
               VALUES ($1::uuid, $2, $3, $4, $5::jsonb)""",
            key["api_key_id"], product, units, status,
            __import__("json").dumps(metadata or {}),
        )

@router.get("/v1/developer/products")
async def list_products():
    return {"products": PRODUCTS, "billing_status": "not_configured"}

@router.post("/v1/developer/keys")
async def create_developer_key(body: CreateKeyRequest, request: Request):
    owner_id = getattr(request.state, "user_id", None)
    if not owner_id:
        raise HTTPException(status_code=401, detail="Sign-in is required; trusted identity middleware must set request.state.user_id")
    pool = await _database(request)
    raw = "oriom_live_" + secrets.token_urlsafe(32)
    prefix = raw[:20]
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    async with pool.acquire() as connection:
        row = await connection.fetchrow(
            """INSERT INTO developer_api_keys (owner_id, name, key_prefix, key_hash, plan_code)
               VALUES ($1, $2, $3, $4, $5)
               RETURNING api_key_id::text, name, key_prefix, plan_code, created_at""",
            str(owner_id), body.name, prefix, digest, body.plan_code,
        )
    return {"key": raw, "warning": "Copy this key now. It cannot be retrieved again.", "record": dict(row)}


@router.get("/v1/developer/keys")
async def list_developer_keys(request: Request):
    owner_id = getattr(request.state, "user_id", None)
    if not owner_id:
        raise HTTPException(status_code=401, detail="Sign-in is required")
    pool = await _database(request)
    async with pool.acquire() as connection:
        rows = await connection.fetch(
            """SELECT api_key_id::text, name, key_prefix, plan_code, created_at, last_used_at, revoked_at
               FROM developer_api_keys WHERE owner_id=$1 ORDER BY created_at DESC LIMIT 100""",
            str(owner_id),
        )
    return {"keys": [dict(row) for row in rows]}

@router.delete("/v1/developer/keys/{api_key_id}")
async def revoke_developer_key(api_key_id: UUID, request: Request):
    owner_id = getattr(request.state, "user_id", None)
    if not owner_id:
        raise HTTPException(status_code=401, detail="Sign-in is required")
    pool = await _database(request)
    async with pool.acquire() as connection:
        row = await connection.fetchrow(
            """UPDATE developer_api_keys SET revoked_at=NOW()
               WHERE api_key_id=$1::uuid AND owner_id=$2 AND revoked_at IS NULL
               RETURNING api_key_id::text""",
            str(api_key_id), str(owner_id),
        )
    if row is None:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"revoked": True, "api_key_id": row["api_key_id"]}

@router.get("/v1/developer/usage")
async def get_developer_usage(request: Request, key: dict = Depends(require_api_key)):
    pool = await _database(request)
    async with pool.acquire() as connection:
        rows = await connection.fetch(
            """SELECT product_code, COUNT(*)::bigint AS requests,
                      COALESCE(SUM(units),0)::bigint AS units,
                      MIN(created_at) AS first_request, MAX(created_at) AS last_request
               FROM developer_api_usage WHERE api_key_id=$1::uuid
                 AND created_at >= date_trunc('month', NOW())
               GROUP BY product_code ORDER BY product_code""",
            key["api_key_id"],
        )
    return {"plan_code": key["plan_code"], "period": "current_calendar_month", "usage": [dict(row) for row in rows]}

@router.post("/v1/embeddings/text")
async def create_text_embeddings(body: EmbeddingRequest, request: Request, key: dict = Depends(require_api_key)):
    provider = getattr(request.app.state, "embedding_provider", None)
    if provider is None:
        raise HTTPException(status_code=503, detail="Embedding provider is not configured")
    texts = [body.input] if isinstance(body.input, str) else body.input
    if not texts or len(texts) > 64 or any(not item.strip() or len(item) > 12000 for item in texts):
        raise HTTPException(status_code=422, detail="Provide 1–64 non-empty texts, each at most 12,000 characters")
    if body.model and body.model != provider.model:
        raise HTTPException(status_code=400, detail="Requested model does not match the configured provider")
    try:
        vectors = await provider.embed(texts)
    except Exception as exc:
        from semantic_index import EmbeddingUnavailable
        if isinstance(exc, EmbeddingUnavailable):
            raise HTTPException(status_code=502, detail="Embedding provider failed") from exc
        raise
    await record_usage(request, key, "embeddings", sum(len(item) for item in texts), 200,
                       {"model": provider.model, "dimensions": provider.dimensions, "input_count": len(texts)})
    return {
        "object": "list",
        "model": provider.model,
        "dimensions": provider.dimensions,
        "data": [{"object": "embedding", "index": index, "embedding": vector} for index, vector in enumerate(vectors)],
        "usage": {"input_characters": sum(len(item) for item in texts)},
    }
