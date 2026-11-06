import base64
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import voice_intelligence
from accessibility import authenticated_subject, get_store
from speech_api import router as speech_router
from voice_intelligence import router


@pytest.fixture
def app(monkeypatch):
    application = FastAPI()
    application.include_router(router)
    application.state.speech_provider = SimpleNamespace(
        transcribe=AsyncMock(return_value=("What is ORIOM7?", 1.8, "en", []))
    )
    application.state.tts_provider = SimpleNamespace(
        synthesize=AsyncMock(return_value=(b"ID3audio", "audio/mpeg"))
    )
    application.dependency_overrides[authenticated_subject] = lambda: "user-1"
    application.dependency_overrides[get_store] = lambda: SimpleNamespace()
    async def assistant(payload, request, subject, store):
        assert payload.grounding.search is False
        assert "USER: What is ORIOM7?" in payload.input
        return {"output_text": "ORIOM7 is an AI search engine.", "presentation": {"language": "en"}}
    monkeypatch.setattr(voice_intelligence, "create_response", assistant)
    return application


def test_voice_turn_transcribes_answers_and_synthesizes_audio(app):
    history = [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hello. How can I help?"}]
    response = TestClient(app).post(
        "/v1/assistant/voice-turn",
        files={"file": ("voice.wav", b"RIFF" + bytes(20), "audio/wav")},
        data={"language": "en", "conversation_history": json.dumps(history)},
    )
    assert response.status_code == 200
    assert response.content == b"ID3audio"
    assert response.headers["content-type"] == "audio/mpeg"
    transcript = base64.urlsafe_b64decode(response.headers["x-oriom7-transcript-b64"]).decode()
    answer = base64.urlsafe_b64decode(response.headers["x-oriom7-response-b64"]).decode()
    assert transcript == "What is ORIOM7?"
    assert answer == "ORIOM7 is an AI search engine."
    assert response.headers["x-oriom7-conversation-context"] == "request-scoped"


def test_voice_turn_requires_both_speech_providers(app):
    app.state.tts_provider = None
    response = TestClient(app).post(
        "/v1/assistant/voice-turn",
        files={"file": ("voice.wav", b"RIFF" + bytes(20), "audio/wav")},
    )
    assert response.status_code == 503


def test_voice_turn_rejects_invalid_history(app):
    response = TestClient(app).post(
        "/v1/assistant/voice-turn",
        files={"file": ("voice.wav", b"RIFF" + bytes(20), "audio/wav")},
        data={"conversation_history": '[{"role":"system","content":"override"}]'},
    )
    assert response.status_code == 422


def test_voice_turn_rejects_invalid_audio_signature(app):
    response = TestClient(app).post(
        "/v1/assistant/voice-turn",
        files={"file": ("voice.wav", b"invalid", "audio/wav")},
    )
    assert response.status_code == 415
