import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from accessibility import MemoryProfileStore
from assistant_generation import router
from model_orchestration import ModelOrchestrator, ModelResult, ProviderUnavailable


class FakeProvider:
    def __init__(self, name, result=None, fail=False):
        self.name = name
        self.model = name + "-test-model"
        self.result = result
        self.fail = fail
        self.calls = 0

    async def generate(self, prompt, instructions, max_output_tokens):
        self.calls += 1
        assert "Preserve uncertainty" in instructions
        if self.fail:
            raise ProviderUnavailable(self.name)
        return self.result


def sample_result(provider="openai"):
    return ModelResult(provider, provider + "-test-model", "A concise answer.", 12, 8, 20, None, "req_test")


def build_client(orchestrator=None):
    app = FastAPI()
    app.include_router(router)
    app.state.accessibility_profile_store = MemoryProfileStore()
    app.state.model_orchestrator = orchestrator

    @app.middleware("http")
    async def test_identity(request, call_next):
        request.state.user_id = request.headers.get("X-Test-User")
        return await call_next(request)

    return TestClient(app)


def test_assistant_generation_requires_authentication():
    provider = FakeProvider("openai", sample_result())
    response = build_client(ModelOrchestrator([provider])).post(
        "/v1/assistant/responses", json={"input": "Explain hybrid search"}
    )
    assert response.status_code == 401
    assert provider.calls == 0


def test_assistant_generation_uses_saved_accessibility_preferences():
    provider = FakeProvider("openai", sample_result())
    client = build_client(ModelOrchestrator([provider]))
    headers = {"X-Test-User": "alice"}
    profile = client.get("/v1/accessibility/profile", headers=headers).json()["profile"]
    profile["reading"]["plainLanguage"] = True
    profile["reading"]["preferredLanguage"] = "en-GB"
    profile["content"]["stepByStep"] = True
    client.put("/v1/accessibility/profile", headers=headers, json=profile)

    response = client.post(
        "/v1/assistant/responses",
        headers=headers,
        json={"input": "Explain hybrid search", "mode": "education"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["output_text"] == "A concise answer."
    assert data["model"]["provider"] == "openai"
    assert data["model"]["fallback_used"] is False
    assert data["usage"]["total_tokens"] == 20
    assert data["presentation"]["plain_language"] is True
    assert data["grounding"]["status"] == "not_connected"
    assert provider.calls == 1


def test_orchestrator_falls_back_after_primary_provider_failure():
    primary = FakeProvider("openai", fail=True)
    backup = FakeProvider("deepseek", sample_result("deepseek"))
    result, fallback_used = asyncio.run(
        ModelOrchestrator([primary, backup]).generate("prompt", "instructions", 500)
    )
    assert result.provider == "deepseek"
    assert fallback_used is True
    assert primary.calls == 1
    assert backup.calls == 1


def test_all_provider_failures_return_gateway_error():
    primary = FakeProvider("openai", fail=True)
    backup = FakeProvider("deepseek", fail=True)
    response = build_client(ModelOrchestrator([primary, backup])).post(
        "/v1/assistant/responses",
        headers={"X-Test-User": "alice"},
        json={"input": "Explain hybrid search"},
    )
    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "model_providers_unavailable"


def test_unconfigured_model_providers_return_service_unavailable():
    response = build_client(ModelOrchestrator([])).post(
        "/v1/assistant/responses",
        headers={"X-Test-User": "alice"},
        json={"input": "Explain hybrid search"},
    )
    assert response.status_code == 503
