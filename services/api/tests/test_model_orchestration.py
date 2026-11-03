import asyncio
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from assistant_generation import router
from model_orchestration import ModelOrchestrator, ModelResult, ProviderUnavailable
from retrieval import RetrievalService, SearchResult


class StaticProfileStore:
    async def get(self, subject):
        return {
            "reading": {"preferredLanguage": "en-GB", "plainLanguage": True, "detailLevel": "concise",
                        "speechOutput": False, "speechRate": 1.0, "highlightSpokenText": False},
            "content": {"showShortAnswerFirst": True, "stepByStep": True, "reduceClutter": True},
            "sensory": {"calmPresentation": False},
        }


class FakeProvider:
    def __init__(self, name, result=None, fail=False):
        self.name, self.model, self.result, self.fail = name, name + "-test-model", result, fail
        self.calls = 0
        self.instructions = []

    async def generate(self, prompt, instructions, max_output_tokens):
        self.calls += 1
        self.instructions.append(instructions)
        if self.fail:
            raise ProviderUnavailable(self.name)
        return self.result


def sample_result(provider="openai"):
    return ModelResult(provider, provider + "-test-model", "A concise answer [S1].", 12, 8, 20, None, "req_test")


def build_client(orchestrator=None):
    app = FastAPI()
    app.include_router(router)
    app.state.accessibility_profile_store = StaticProfileStore()
    app.state.model_orchestrator = orchestrator
    class TestIndex:
        async def search(self, query, limit, language=None):
            return [SearchResult(
                source_id="doc-1", title="Grid battery evidence",
                canonical_url="https://example.org/battery",
                snippet="A verified excerpt about grid batteries.",
                provider="oriom7_index", source_type="oriom7_index",
                fetched_at=datetime(2026, 11, 3, tzinfo=timezone.utc),
                published_at=None, language="en", score=0.9,
            )]
    app.state.retrieval_service = RetrievalService(TestIndex())

    @app.middleware("http")
    async def test_identity(request, call_next):
        request.state.user_id = request.headers.get("X-Test-User")
        return await call_next(request)

    return TestClient(app)


def test_generation_requires_authentication():
    provider = FakeProvider("openai", sample_result())
    response = build_client(ModelOrchestrator([provider])).post("/v1/assistant/responses", json={"input": "Explain hybrid search"})
    assert response.status_code == 401
    assert provider.calls == 0


def test_generation_applies_accessibility_preferences():
    provider = FakeProvider("openai", sample_result())
    response = build_client(ModelOrchestrator([provider])).post(
        "/v1/assistant/responses", headers={"X-Test-User": "alice"},
        json={"input": "Explain hybrid search", "mode": "education"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["output_text"] == "A concise answer [S1]."
    assert data["model"]["provider"] == "openai"
    assert data["model"]["fallback_used"] is False
    assert data["usage"]["total_tokens"] == 20
    assert data["presentation"]["plain_language"] is True
    assert data["presentation"]["language"] == "en-GB"
    assert data["grounding"]["status"] == "grounded"
    assert data["grounding"]["citations"][0]["id"] == "S1"
    assert data["grounding"]["citation_validation"]["status"] == "valid"
    assert provider.calls == 1
    assert "Preserve uncertainty" in provider.instructions[0]


def test_orchestrator_uses_fallback_after_primary_failure():
    primary, backup = FakeProvider("openai", fail=True), FakeProvider("deepseek", sample_result("deepseek"))
    result, fallback_used = asyncio.run(ModelOrchestrator([primary, backup]).generate("prompt", "instructions", 500))
    assert result.provider == "deepseek"
    assert fallback_used is True
    assert primary.calls == backup.calls == 1


def test_all_provider_failures_return_gateway_error():
    orchestrator = ModelOrchestrator([FakeProvider("openai", fail=True), FakeProvider("deepseek", fail=True)])
    response = build_client(orchestrator).post(
        "/v1/assistant/responses", headers={"X-Test-User": "alice"}, json={"input": "Explain hybrid search"}
    )
    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "model_providers_unavailable"


def test_unconfigured_providers_return_service_unavailable():
    response = build_client(ModelOrchestrator([])).post(
        "/v1/assistant/responses", headers={"X-Test-User": "alice"}, json={"input": "Explain hybrid search"}
    )
    assert response.status_code == 503
