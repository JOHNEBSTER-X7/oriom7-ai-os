"""Permission-aware first-party lexical retrieval and search API."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from accessibility import authenticated_subject

router = APIRouter(prefix="/v1", tags=["search"])


@dataclass(frozen=True)
class SearchResult:
    source_id: str
    title: str
    canonical_url: str
    snippet: str
    provider: str
    source_type: str
    fetched_at: datetime
    published_at: datetime | None
    language: str | None
    score: float


class SearchIndex(Protocol):
    async def search(self, query: str, limit: int, language: str | None = None) -> list[SearchResult]: ...


class ExternalSearchProvider(Protocol):
    """Contract for approved external search adapters; not a live provider."""
    name: str

    async def search(self, query: str, limit: int, language: str | None = None) -> list[SearchResult]: ...


class PostgresLexicalIndex:
    """PostgreSQL full-text retrieval over documents admitted to the owned index."""

    def __init__(self, pool):
        self.pool = pool

    async def search(self, query: str, limit: int, language: str | None = None) -> list[SearchResult]:
        sql = """
            SELECT document_id::text AS source_id,
                   title,
                   canonical_url,
                   ts_headline('simple', body_text, websearch_to_tsquery('simple', $1),
                     'MaxFragments=2,MaxWords=35,MinWords=12,StartSel=<mark>,StopSel=</mark>') AS snippet,
                   provider,
                   fetched_at,
                   published_at,
                   language,
                   ts_rank(search_vector, websearch_to_tsquery('simple', $1)) AS score
            FROM search_documents
            WHERE deleted_at IS NULL
              AND index_status = 'indexed'
              AND rights_basis IS NOT NULL AND btrim(rights_basis) <> ''
              AND search_vector @@ websearch_to_tsquery('simple', $1)
              AND ($3::text IS NULL OR language = $3)
            ORDER BY score DESC, fetched_at DESC
            LIMIT $2
        """
        async with self.pool.acquire() as connection:
            rows = await connection.fetch(sql, query, limit, language)
        return [
            SearchResult(
                source_id=row["source_id"],
                title=row["title"],
                canonical_url=row["canonical_url"],
                snippet=row["snippet"],
                provider=row["provider"] or "oriom7_index",
                source_type="oriom7_index",
                fetched_at=row["fetched_at"],
                published_at=row["published_at"],
                language=row["language"],
                score=float(row["score"]),
            )
            for row in rows
        ]


class RetrievalService:
    def __init__(self, owned_index: SearchIndex | None, external_providers: list[ExternalSearchProvider] | None = None):
        self.owned_index = owned_index
        self.external_providers = external_providers or []

    async def search(self, query: str, limit: int, language: str | None = None,
                     include_owned: bool = True, include_external: bool = False) -> list[SearchResult]:
        results: list[SearchResult] = []
        if include_owned and self.owned_index is not None:
            results.extend(await self.owned_index.search(query, limit, language))
        if include_external:
            for provider in self.external_providers:
                results.extend(await provider.search(query, limit, language))
        # Stable URL deduplication, preferring the higher-scoring candidate.
        deduplicated: dict[str, SearchResult] = {}
        for result in sorted(results, key=lambda item: item.score, reverse=True):
            deduplicated.setdefault(result.canonical_url, result)
        return list(deduplicated.values())[:limit]


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=10, ge=1, le=50)
    language: str | None = Field(default=None, max_length=35)
    sources: list[str] = Field(default_factory=lambda: ["oriom7_index"], max_length=2)

    @field_validator("sources")
    @classmethod
    def validate_sources(cls, value):
        allowed = {"oriom7_index", "external"}
        if not value or any(source not in allowed for source in value):
            raise ValueError("sources must contain oriom7_index and/or external")
        return list(dict.fromkeys(value))


@router.post("/search")
async def search(
    payload: SearchRequest,
    request: Request,
    subject: str = Depends(authenticated_subject),
) -> dict:
    service: RetrievalService | None = getattr(request.app.state, "retrieval_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail={
            "code": "search_index_not_configured",
            "message": "The ORIOM7 search index is not configured.",
        })
    results = await service.search(
        payload.query, payload.limit, payload.language,
        include_owned="oriom7_index" in payload.sources,
        include_external="external" in payload.sources,
    )
    unavailable_sources = []
    if "external" in payload.sources and not service.external_providers:
        unavailable_sources.append("external")
    if "oriom7_index" in payload.sources and service.owned_index is None:
        unavailable_sources.append("oriom7_index")
    return {
        "query": payload.query,
        "status": "partial" if unavailable_sources else "completed",
        "unavailable_sources": unavailable_sources,
        "results": [
            {
                "id": result.source_id,
                "title": result.title,
                "url": result.canonical_url,
                "snippet": result.snippet,
                "source_type": result.source_type,
                "provider": result.provider,
                "retrieved_at": result.fetched_at.isoformat(),
                "published_at": result.published_at.isoformat() if result.published_at else None,
                "language": result.language,
                "score": result.score,
            }
            for result in results
        ],
        "external_search_configured": bool(service.external_providers),
    }
