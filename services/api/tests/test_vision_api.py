from types import SimpleNamespace
from unittest.mock import AsyncMock

import commercial_api
import vision_api
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from vision_api import router


@pytest.fixture
def app():
    application = FastAPI()
    application.include_router(router)
    application.state.vision_provider = SimpleNamespace(
        analyze=AsyncMock(return_value={
            "description": "A red bicycle leaning against a brick wall.",
            "answer": "The bicycle is red.",
            "objects": ["bicycle", "brick wall"],
            "text_found": [],
        })
    )
    application.dependency_overrides[commercial_api.require_api_key] = lambda: {
        "api_key_id": "00000000-0000-0000-0000-000000000001",
        "owner_id": "acct",
        "plan_code": "starter",
    }
    return application


def test_vision_returns_description_and_meters_one_image(app, monkeypatch):
    usage = AsyncMock()
    monkeypatch.setattr(vision_api, "record_usage", usage)
    response = TestClient(app).post(
        "/v1/vision/analyze",
        files={"file": ("bike.jpg", b"\xff\xd8\xfffake-image", "image/jpeg")},
        data={"question": "What colour is the bicycle?"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["description"].startswith("A red bicycle")
    assert payload["answer"] == "The bicycle is red."
    assert payload["objects"] == ["bicycle", "brick wall"]
    assert payload["storage"] == "not_persisted"
    usage.assert_awaited_once()
    assert usage.await_args.args[3] == 1


def test_vision_rejects_mismatched_signature(app):
    response = TestClient(app).post(
        "/v1/vision/analyze",
        files={"file": ("photo.jpg", b"not a jpeg", "image/jpeg")},
    )
    assert response.status_code == 415


def test_vision_rejects_unsupported_media_type(app):
    response = TestClient(app).post(
        "/v1/vision/analyze",
        files={"file": ("photo.gif", b"GIF89a", "image/gif")},
    )
    assert response.status_code == 415


def test_vision_requires_configured_provider(app):
    app.state.vision_provider = None
    response = TestClient(app).post(
        "/v1/vision/analyze",
        files={"file": ("photo.png", b"\x89PNG\r\n\x1a\nimage", "image/png")},
    )
    assert response.status_code == 503


def test_vision_provider_requires_https():
    with pytest.raises(ValueError):
        vision_api.VisualIntelligenceProvider("http://localhost/vision", None)


def test_vision_rejects_invalid_provider_description(app):
    app.state.vision_provider.analyze.return_value = {"description": ""}
    response = TestClient(app).post(
        "/v1/vision/analyze",
        files={"file": ("photo.jpg", b"\xff\xd8\xfffake", "image/jpeg")},
    )
    assert response.status_code == 502
