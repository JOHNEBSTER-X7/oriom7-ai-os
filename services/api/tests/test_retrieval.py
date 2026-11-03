from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from retrieval import RetrievalService, SearchRequest, SearchResult, router


def item(source_id, url, score=1.0, provider="oriom7_index"):
    return SearchResult(
        source_id=source_id,
        title="Grid battery research",
        canonical_url=url,
        snippet="A retrieved passage about grid batteries.",
        provider=provider,
        source_type="oriom7_index",
        fetched_at=datetime(2026, 11, 3, tzinfo=timezone.utc),
        published_at=None,
        language="en",
        score=score,
    )


class FakeIndex:
    def __init__(self, results):
        self.results = results
        self.calls = []

    async def search(self, query, limit, language=None):
        self.calls.append((query, limit, language))
        return sorted(self.results, key=lambda result: result.score, reverse=True)[:limit]


class FakeExternal:
    name = "external-test"

    async def search(self, query, limit, language=None):
        return [item("ext-1", "https://example.org/external", 2.0, self.name)]


def test_retrieval_deduplicates_canonical_urls_and_keeps_best_score():
    index = FakeIndex([
        item("doc-1", "https://example.org/article", 0.4),
        item("doc-2", "https://example.org/article", 0.9),
        item("doc-3", "https://example.org/other", 0.7),
    ])
    results = __import__("asyncio").run(RetrievalService(index).search("battery", 10))
    assert len(results) == 2
    assert results[0].source_id == "doc-2"


def test_retrieval_can_include_external_adapter_results():
    index = FakeIndex([item("doc-1", "https://example.org/owned")])
    service = RetrievalService(index, [FakeExternal()])
    results = __import__("asyncio").run(
        service.search("battery", 10, include_owned=True, include_external=True)
    )
    assert {result.provider for result in results} == {"oriom7_index", "external-test"}


def test_search_request_rejects_unknown_source():
    try:
        SearchRequest(query="battery", sources=["untrusted"])
        assert False, "invalid source should be rejected"
    except ValueError:
        pass


def test_search_endpoint_requires_authenticated_identity():
    app = FastAPI()
    app.include_router(router)
    app.state.retrieval_service = RetrievalService(FakeIndex([item("doc-1", "https://example.org/a")]))

    @app.middleware("http")
    async def test_identity(request, call_next):
        request.state.user_id = None
        return await call_next(request)

    response = TestClient(app).post("/v1/search", json={"query": "battery"})
    assert response.status_code == 401


def test_search_endpoint_returns_normalised_provenance():
    app = FastAPI()
    app.include_router(router)
    app.state.retrieval_service = RetrievalService(FakeIndex([item("doc-1", "https://example.org/a")]))

    @app.middleware("http")
    async def test_identity(request, call_next):
        request.state.user_id = "alice"
        return await call_next(request)

    response = TestClient(app).post("/v1/search", json={"query": "battery"})
    assert response.status_code == 200
    data = response.json()
    assert data["results"][0]["id"] == "doc-1"
    assert data["results"][0]["url"] == "https://example.org/a"
    assert data["results"][0]["source_type"] == "oriom7_index"
