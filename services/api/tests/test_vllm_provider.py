import asyncio

import httpx
import model_orchestration


def test_vllm_chat_completions_provider_parses_response(monkeypatch):
    class FakeResponse:
        def raise_for_status(self): pass
        def json(self):
            return {
                "id": "req-123", "model": "local-model",
                "choices": [{"message": {"content": "Local model response"}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
            }

    class FakeClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, headers, json):
            assert url == "http://vllm:8000/v1/chat/completions"
            assert json["messages"][0]["role"] == "system"
            assert json["stream"] is False
            return FakeResponse()

    monkeypatch.setattr(model_orchestration.httpx, "AsyncClient", FakeClient)
    provider = model_orchestration.ChatCompletionsProvider(
        "vllm", "http://vllm:8000/v1", "local-key", "local-model"
    )
    result = asyncio.run(provider.generate("prompt", "instructions", 200))
    assert result.text == "Local model response"
    assert result.input_tokens == 12
    assert result.output_tokens == 8
    assert result.provider_request_id == "req-123"


def test_vllm_environment_registers_openai_compatible_provider(monkeypatch):
    monkeypatch.setenv("ORIOM7_VLLM_BASE_URL", "http://vllm:8000/v1")
    monkeypatch.setenv("ORIOM7_VLLM_MODEL", "local-model")
    monkeypatch.setenv("ORIOM7_VLLM_API_KEY", "local-key")
    monkeypatch.setenv("ORIOM7_MODEL_PRIMARY", "vllm")
    monkeypatch.setenv("ORIOM7_MODEL_FALLBACK", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ORIOM7_OPENAI_MODEL", raising=False)
    orchestrator = model_orchestration.build_orchestrator_from_env()
    assert orchestrator.providers
    assert orchestrator.providers[0].name == "vllm"
    assert isinstance(orchestrator.providers[0], model_orchestration.ChatCompletionsProvider)
