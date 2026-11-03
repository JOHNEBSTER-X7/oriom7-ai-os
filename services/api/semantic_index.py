"""Optional multilingual embeddings and pgvector indexing.

Uses an OpenAI-compatible embeddings endpoint. Document text is sent to the
configured provider only when an embedding provider is explicitly configured.
"""
from __future__ import annotations

import asyncio
import logging
import os

import asyncpg
import httpx

from retrieval import SearchResult

logger = logging.getLogger("oriom7.semantic_search")
VECTOR_DIMENSIONS = 1536


class EmbeddingUnavailable(Exception):
    pass


class EmbeddingProvider:
    def __init__(self, api_key: str, model: str, base_url: str, timeout: float = 25.0):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts or any(not text.strip() for text in texts):
            raise ValueError("Embedding input must contain non-empty text")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": self.model, "input": texts, "encoding_format": "float"},
                )
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(data, list) or len(data) != len(texts):
                raise ValueError("Embedding response shape is invalid")
            ordered = sorted(data, key=lambda item: item.get("index", 0))
            vectors = [item.get("embedding") for item in ordered]
            for vector in vectors:
                if (not isinstance(vector, list) or len(vector) != VECTOR_DIMENSIONS
                        or any(not isinstance(value, (int, float)) for value in vector)):
                    raise ValueError("Embedding dimensions or values are invalid")
            return [[float(value) for value in vector] for vector in vectors]
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            logger.warning("embedding_provider_failed", extra={"model": self.model})
            raise EmbeddingUnavailable(self.model) from exc

    async def index_document(self, pool, document_id: str, text: str, content_hash: str) -> None:
        # Keep request payloads bounded; title + body text are already capped by ingestion.
        vector = (await self.embed([text[:12000]]))[0]
        literal = "[" + ",".join(f"{value:.8f}" for value in vector) + "]"
        async with pool.acquire() as connection:
            await connection.execute(
                """INSERT INTO search_document_embeddings
                   (document_id, embedding_model, embedding, content_hash, embedded_at)
                   SELECT $1::uuid, $2, $3::vector, $4, NOW()
                   FROM search_documents d
                   WHERE d.document_id = $1::uuid AND d.deleted_at IS NULL
                     AND d.index_status = 'indexed' AND d.content_hash = $4
                   ON CONFLICT (document_id) DO UPDATE SET
                     embedding_model = EXCLUDED.embedding_model,
                     embedding = EXCLUDED.embedding,
                     content_hash = EXCLUDED.content_hash,
                     embedded_at = NOW()""",
                document_id, self.model, literal, content_hash,
            )


class PostgresVectorIndex:
    def __init__(self, pool, embedder: EmbeddingProvider):
        self.pool = pool
        self.embedder = embedder

    async def search(self, query: str, limit: int, language: str | None = None) -> list[SearchResult]:
        vector = (await self.embedder.embed([query]))[0]
        literal = "[" + ",".join(f"{value:.8f}" for value in vector) + "]"
        async with self.pool.acquire() as connection:
            rows = await connection.fetch(
                """SELECT d.document_id::text AS source_id, d.title, d.canonical_url,
                          left(d.body_text, 1200) AS snippet, d.provider, d.fetched_at,
                          d.published_at, d.language,
                          1 - (e.embedding <=> $1::vector) AS score
                   FROM search_document_embeddings e
                   JOIN search_documents d ON d.document_id = e.document_id
                   WHERE d.deleted_at IS NULL AND d.index_status = 'indexed'
                     AND d.rights_basis IS NOT NULL AND btrim(d.rights_basis) <> ''
                     AND d.robots_status IN ('allowed', 'not_applicable')
                     AND e.embedding_model = $2
                     AND ($4::text IS NULL OR d.language = $4
                          OR split_part(d.language, '-', 1) = split_part($4, '-', 1))
                   ORDER BY e.embedding <=> $1::vector
                   LIMIT $3""",
                literal, self.embedder.model, limit, language,
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
    if not api_key:
        return None
    return EmbeddingProvider(api_key, model, base_url)


async def backfill_missing_embeddings(pool, embedder: EmbeddingProvider, batch_size: int = 20) -> int:
    """Embed eligible documents missing a current-model vector in bounded batches."""
    total = 0
    while True:
        async with pool.acquire() as connection:
            rows = await connection.fetch(
                """SELECT d.document_id::text, d.body_text, d.content_hash
                   FROM search_documents d
                   LEFT JOIN search_document_embeddings e ON e.document_id = d.document_id
                   WHERE d.deleted_at IS NULL AND d.index_status = 'indexed'
                     AND d.rights_basis IS NOT NULL AND btrim(d.rights_basis) <> ''
                     AND d.robots_status IN ('allowed', 'not_applicable')
                     AND (e.document_id IS NULL OR e.embedding_model <> $1
                          OR e.content_hash <> d.content_hash)
                   ORDER BY d.fetched_at DESC LIMIT $2""",
                embedder.model, batch_size,
            )
        if not rows:
            return total
        texts = [row["body_text"][:12000] for row in rows]
        vectors = await embedder.embed(texts)
        async with pool.acquire() as connection:
            async with connection.transaction():
                for row, vector in zip(rows, vectors):
                    literal = "[" + ",".join(f"{value:.8f}" for value in vector) + "]"
                    await connection.execute(
                        """INSERT INTO search_document_embeddings
                           (document_id, embedding_model, embedding, content_hash)
                           VALUES ($1::uuid, $2, $3::vector, $4)
                           ON CONFLICT (document_id) DO UPDATE SET
                             embedding_model = EXCLUDED.embedding_model,
                             embedding = EXCLUDED.embedding,
                             content_hash = EXCLUDED.content_hash, embedded_at = NOW()""",
                        row["document_id"], embedder.model, literal, row["content_hash"],
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
        print(f"Indexed {count} document embeddings")
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(backfill_main())
