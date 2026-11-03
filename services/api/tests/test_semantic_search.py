from datetime import datetime, timezone

import asyncio
import pytest

from retrieval import RetrievalService, SearchResult
from semantic_index import EmbeddingProvider, EmbeddingUnavailable, VECTOR_DIMENSIONS


def result(source_id, url, score, provider):
    return SearchResult(
        source_id=source_id, title="Multilingual battery research",
        canonical_url=url, snippet="Battery storage research",
        provider=provider, source_type="oriom7_index",
        fetched_at=datetime(2026, 11, 3, tzinfo=timezone.utc),
        published_at=None, language="es", score=score,
    )


class RankedIndex:
    def __init__(self, rows):
        self.rows = rows

    async def search(self, query, limit, language=None):
        return self.rows[:limit]


def test_rrf_accumulates_support_for_same_url_across_lexical_and_semantic():
    lexical = RankedIndex([
        result("doc-a", "https://example.org/a", 0.9, "lexical"),
        result("doc-b", "https://example.org/b", 0.8, "lexical"),
    ])
    semantic = RankedIndex([
        result("doc-a", "https://example.org/a", 0.8, "semantic"),
        result("doc-c", "https://example.org/c", 0.7, "semantic"),
    ])
    results = asyncio.run(
        RetrievalService(lexical, semantic_index=semantic).search("batería", 10)
    )
    assert results[0].canonical_url == "https://example.org/a"
    assert len(results) == 3
    assert results[0].score > results[1].score


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    payload = None

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, *args, **kwargs):
        return FakeResponse(self.payload)


def test_embedding_provider_accepts_valid_1536_dimension_vectors(monkeypatch):
    vector = [0.01] * VECTOR_DIMENSIONS
    FakeClient.payload = {"data": [{"index": 0, "embedding": vector}]}
    monkeypatch.setattr("semantic_index.httpx.AsyncClient", FakeClient)
    provider = EmbeddingProvider("test-key", "test-model", "https://example.test/v1")
    result_vectors = asyncio.run(provider.embed(["hola mundo"]))
    assert len(result_vectors) == 1
    assert len(result_vectors[0]) == VECTOR_DIMENSIONS


def test_embedding_provider_rejects_wrong_vector_dimensions(monkeypatch):
    FakeClient.payload = {"data": [{"index": 0, "embedding": [0.1, 0.2]}]}
    monkeypatch.setattr("semantic_index.httpx.AsyncClient", FakeClient)
    provider = EmbeddingProvider("test-key", "test-model", "https://example.test/v1")
    with pytest.raises(EmbeddingUnavailable):
        asyncio.run(provider.embed(["hello world"]))
