"""Configurable-dimensional embeddings and pgvector indexing for ORIOM7.

The default remains 1,536 dimensions for backwards compatibility. A model's
dimension is explicit configuration and is stored with every vector. Vectors
from different models or dimensions are never compared with one another.
"""
from __future__ import annotations

import asyncio
import logging
import math
import os

import asyncpg
import httpx

from retrieval import SearchResult

logger = logging.getLogger("oriom7.semantic_search")
DEFAULT_VECTOR_DIMENSIONS = 1536
VECTOR_DIMENSIONS = DEFAULT_VECTOR_DIMENSIONS
MAX_VECTOR_DIMENSIONS = 16000
HNSW_MAX_VECTOR_DIMENSIONS = 2000


class EmbeddingUnavailable(Exception):
    pass


class EmbeddingProvider:
    def __init__(self, api_key: str, model: str, base_url: str,
                 dimensions: int = DEFAULT_VECTOR_DIMENSIONS, timeout: float = 25.0):
        if not 1 <= dimensions <= MAX_VECTOR_DIMENSIONS:
            raise ValueError(f"dimensions must be between 1 and {MAX_VECTOR_DIMENSIONS}")
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.dimensions = dimensions
        self.timeout = timeout

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts or any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValueError("Embedding input must contain non-empty text")
        request_body = {"model": self.model, "input": texts, "encoding_format": "float"}
        if self.dimensions != DEFAULT_VECTOR_DIMENSIONS:
            request_body["dimensions"] = self.dimensions
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=request_body,
                )
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(data, list) or len(data) != len(texts):
                raise ValueError("Embedding response shape is invalid")
            ordered = sorted(data, key=lambda item: item.get("index", 0))
            vectors = [item.get("embedding") for item in ordered]
            for vector in vectors:
                if (not isinstance(vector, list) or len(vector) != self.dimensions
                        or any(isinstance(value, bool) or not isinstance(value, (int, float))
                               or not math.isfinite(value) for value in vector)):
                    raise ValueError("Embedding dimensions or values are invalid")
            return [[float(value) for value in vector] for vector in vectors]
        except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError) as exc:
            logger.warning("embedding_provider_failed", extra={"model": self.model})
            raise EmbeddingUnavailable(self.model) from exc

    async def index_document(self, pool, document_id: str, text: str, content_hash: str) -> None:
        vector = (await self.embed([text[:12000]]))[0]
        literal = "[" + ",".join(f"{value:.8f}" for value in vector) + "]"
        async with pool.acquire() as connection:
            await connection.execute(
                """INSERT INTO search_document_embeddings
                   (document_id, embedding_model, embedding, embedding_dimensions,
                    content_hash, embedded_at)
                   SELECT $1::uuid, $2, $3::vector, $5, $4, NOW()
                   FROM search_documents d
                   WHERE d.document_id = $1::uuid AND d.deleted_at IS NULL
                     AND d.index_status = 'indexed' AND d.content_hash = $4
                   ON CONFLICT (document_id, embedding_model) DO UPDATE SET
                     embedding = EXCLUDED.embedding,
                     embedding_dimensions = EXCLUDED.embedding_dimensions,
                     content_hash = EXCLUDED.content_hash,
                     embedded_at = NOW()""",
                document_id, self.model, literal, content_hash, self.dimensions,
            )


class PostgresVectorIndex:
    def __init__(self, pool, embedder: EmbeddingProvider):
        self.pool = pool
        self.embedder = embedder

    async def search(self, query: str, limit: int, language: str | None = None) -> list[SearchResult]:
        vector = (await self.embedder.embed([query]))[0]
        literal = "[" + ",".join(f"{value:.8f}" for value in vector) + "]"
        # HNSW vector indexes support up to 2,000 dimensions. Higher-dimensional
        # vectors use exact cosine ranking instead of truncation or failure.
        dimension_predicate = (
            "e.embedding_dimensions <= 2000"
            if self.embedder.dimensions <= HNSW_MAX_VECTOR_DIMENSIONS
            else "e.embedding_dimensions > 2000"
        )
        sql = f"""SELECT d.document_id::text AS source_id, d.title, d.canonical_url,
                          left(d.body_text, 1200) AS snippet, d.provider, d.fetched_at,
                          d.published_at, d.language,
                          1 - (e.embedding <=> $1::vector) AS score
                   FROM search_document_embeddings e
                   JOIN search_documents d ON d.document_id = e.document_id
                   WHERE d.deleted_at IS NULL AND d.index_status = 'indexed'
                     AND d.rights_basis IS NOT NULL AND btrim(d.rights_basis) <> ''
                     AND d.robots_status IN ('allowed', 'not_applicable')
                     AND e.embedding_model = $2
                     AND e.embedding_dimensions = $3
                     AND {dimension_predicate}
                     AND ($4::text IS NULL OR d.language = $4
                          OR split_part(d.language, '-', 1) = split_part($4, '-', 1))
                   ORDER BY e.embedding <=> $1::vector
                   LIMIT $5"""
        async with self.pool.acquire() as connection:
            rows = await connection.fetch(
                sql, literal, self.embedder.model, self.embedder.dimensions,
                language if os.getenv("ORIOM7_SEMANTIC_LANGUAGE_FILTER", "false").lower() == "true" else None,
                limit,
            )
        return [
            SearchResult(
                source_id=row["source_id"], title=row["title"],
                canonical_url=row["canonical_url"], snippet=row["snippet"],
                provider=row["provider"] or "oriom7_index", source_type="oriom7_index",
                fetched_at=row["fetched_at"], published_at=row["published_at"],
                language=row["language"], score=float(row["score"]),
            )
            for row in rows
        ]


def build_embedding_provider_from_env() -> EmbeddingProvider | None:
    api_key = os.getenv("ORIOM7_EMBEDDING_API_KEY") or os.getenv("OPENAI_API_KEY")
    model = os.getenv("ORIOM7_EMBEDDING_MODEL", "text-embedding-3-small")
    base_url = os.getenv("ORIOM7_EMBEDDING_BASE_URL", "https://api.openai.com/v1")
    try:
        dimensions = int(os.getenv("ORIOM7_EMBEDDING_DIMENSIONS", str(DEFAULT_VECTOR_DIMENSIONS)))
    except ValueError as exc:
        raise RuntimeError("ORIOM7_EMBEDDING_DIMENSIONS must be an integer") from exc
    if not 1 <= dimensions <= MAX_VECTOR_DIMENSIONS:
        raise RuntimeError(f"ORIOM7_EMBEDDING_DIMENSIONS must be between 1 and {MAX_VECTOR_DIMENSIONS}")
    if not api_key:
        return None
    return EmbeddingProvider(api_key, model, base_url, dimensions=dimensions)


async def backfill_missing_embeddings(pool, embedder: EmbeddingProvider, batch_size: int = 20) -> int:
    """Embed eligible documents missing this model/dimension or a current content hash."""
    total = 0
    while True:
        async with pool.acquire() as connection:
            rows = await connection.fetch(
                """SELECT d.document_id::text, d.body_text, d.content_hash
                   FROM search_documents d
                   LEFT JOIN search_document_embeddings e
                     ON e.document_id = d.document_id AND e.embedding_model = $1
                   WHERE d.deleted_at IS NULL AND d.index_status = 'indexed'
                     AND d.rights_basis IS NOT NULL AND btrim(d.rights_basis) <> ''
                     AND d.robots_status IN ('allowed', 'not_applicable')
                     AND (e.document_id IS NULL OR e.embedding_dimensions <> $2
                          OR e.content_hash <> d.content_hash)
                   ORDER BY d.fetched_at DESC LIMIT $3""",
                embedder.model, embedder.dimensions, batch_size,
            )
        if not rows:
            return total
        vectors = await embedder.embed([row["body_text"][:12000] for row in rows])
        async with pool.acquire() as connection:
            async with connection.transaction():
                for row, vector in zip(rows, vectors):
                    literal = "[" + ",".join(f"{value:.8f}" for value in vector) + "]"
                    await connection.execute(
                        """INSERT INTO search_document_embeddings
                           (document_id, embedding_model, embedding, embedding_dimensions, content_hash)
                           VALUES ($1::uuid, $2, $3::vector, $4, $5)
                           ON CONFLICT (document_id, embedding_model) DO UPDATE SET
                             embedding = EXCLUDED.embedding,
                             embedding_dimensions = EXCLUDED.embedding_dimensions,
                             content_hash = EXCLUDED.content_hash, embedded_at = NOW()""",
                        row["document_id"], embedder.model, literal,
                        embedder.dimensions, row["content_hash"],
                    )
        total += len(rows)


async def backfill_main():
    database_url = os.getenv("DATABASE_URL")
    embedder = build_embedding_provider_from_env()
    if not database_url or not embedder:
        raise RuntimeError("DATABASE_URL and an embedding API key are required")
    pool = await asyncpg.create_pool(database_url, min_size=1, max_size=3)
    try:
        count = await backfill_missing_embeddings(pool, embedder)
        print(f"Indexed {count} document embeddings for {embedder.model} ({embedder.dimensions} dimensions)")
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(backfill_main())
