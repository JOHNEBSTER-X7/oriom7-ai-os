from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import translation_api
import commercial_api
from translation_api import router

@pytest.fixture
def app(monkeypatch):
    application = FastAPI()
    application.include_router(router)
    application.state.translation_provider = SimpleNamespace(
        translate=AsyncMock(return_value="Bonjour le monde")
    )
    application.dependency_overrides[commercial_api.require_api_key] = lambda: {"api_key_id": "00000000-0000-0000-0000-000000000001", "owner_id": "acct", "plan_code": "starter"}
    monkeypatch.setattr(translation_api, "record_usage", AsyncMock())
    return application

def test_translation_endpoint_returns_translation_and_metered_usage(app):
    response = TestClient(app).post(
        "/v1/translation/text",
        json={"text": "Hello world", "source": "en", "target": "fr"},
    )
    assert response.status_code == 200
    assert response.json()["translated_text"] == "Bonjour le monde"
    assert response.json()["usage"]["input_characters"] == 11

def test_translation_rejects_same_source_and_target(app):
    response = TestClient(app).post(
        "/v1/translation/text",
        json={"text": "Hello", "source": "en", "target": "EN"},
    )
    assert response.status_code == 422

def test_translation_is_unavailable_without_provider(app):
    app.state.translation_provider = None
    response = TestClient(app).post(
        "/v1/translation/text",
        json={"text": "Hello", "source": "en", "target": "fr"},
    )
    assert response.status_code == 503

def test_provider_rejects_non_https_endpoint():
    with pytest.raises(ValueError):
        translation_api.TranslationProvider("http://127.0.0.1:8080/translate", None)
