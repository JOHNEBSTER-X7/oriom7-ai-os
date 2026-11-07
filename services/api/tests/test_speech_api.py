from types import SimpleNamespace
from unittest.mock import AsyncMock

import commercial_api
import speech_api
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from speech_api import router


@pytest.fixture
def app():
    application = FastAPI()
    application.include_router(router)
    application.state.speech_provider = SimpleNamespace(
        transcribe=AsyncMock(return_value=("Hello world", 2.2, "en", [
            {"start": 0.0, "end": 2.0, "text": "Hello world", "speaker": "speaker_1"}
        ]))
    )
    application.state.tts_provider = SimpleNamespace(
        synthesize=AsyncMock(return_value=(b"ID3fake-mp3", "audio/mpeg"))
    )
    application.dependency_overrides[commercial_api.require_api_key] = lambda: {
        "api_key_id": "00000000-0000-0000-0000-000000000001",
        "owner_id": "acct", "plan_code": "starter",
    }
    return application


def test_transcription_returns_segments_and_meters_audio_seconds(app, monkeypatch):
    usage = AsyncMock()
    monkeypatch.setattr(speech_api, "record_usage", usage)
    response = TestClient(app).post(
        "/v1/speech/transcriptions",
        files={"file": ("clip.wav", b"RIFF" + bytes(20), "audio/wav")},
        data={"language": "en"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["text"] == "Hello world"
    assert payload["segments"][0]["speaker"] == "speaker_1"
    assert payload["usage"]["audio_seconds"] == 3
    assert payload["storage"] == "not_persisted"
    usage.assert_awaited_once()
    assert usage.await_args.args[3] == 3


def test_transcription_rejects_invalid_signature(app):
    response = TestClient(app).post(
        "/v1/speech/transcriptions",
        files={"file": ("clip.wav", b"invalid", "audio/wav")},
    )
    assert response.status_code == 415


def test_transcription_requires_configured_provider(app):
    app.state.speech_provider = None
    response = TestClient(app).post(
        "/v1/speech/transcriptions",
        files={"file": ("clip.wav", b"RIFF" + bytes(20), "audio/wav")},
    )
    assert response.status_code == 503


def test_speech_provider_requires_https():
    with pytest.raises(ValueError):
        speech_api.SpeechRecognitionProvider("http://localhost/transcribe", None)


def test_synthesis_returns_audio_and_meters_characters(app, monkeypatch):
    usage = AsyncMock()
    monkeypatch.setattr(speech_api, "record_usage", usage)
    response = TestClient(app).post(
        "/v1/speech/synthesis",
        json={"text": "Hello there", "voice": "voice-1", "format": "mp3"},
    )
    assert response.status_code == 200
    assert response.content == b"ID3fake-mp3"
    assert response.headers["content-type"] == "audio/mpeg"
    usage.assert_awaited_once()
    assert usage.await_args.args[3] == len("Hello there")


def test_synthesis_rejects_missing_provider(app):
    app.state.tts_provider = None
    response = TestClient(app).post("/v1/speech/synthesis", json={"text": "Hello"})
    assert response.status_code == 503


def test_synthesis_rejects_invalid_provider_audio(app):
    app.state.tts_provider.synthesize.return_value = (b"invalid", "text/plain")
    response = TestClient(app).post("/v1/speech/synthesis", json={"text": "Hello"})
    assert response.status_code == 502
