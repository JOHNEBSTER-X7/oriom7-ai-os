from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import commercial_api
import pytest
import visual_search
from fastapi import FastAPI
from fastapi.testclient import TestClient


class Connection:
    def __init__(self):
        self.fetchrow = AsyncMock(return_value={
            "visual_item_id": "00000000-0000-0000-0000-000000000111",
            "created_at": datetime.now(timezone.utc),
        })
        self.fetch = AsyncMock(return_value=[{
            "id": "00000000-0000-0000-0000-000000000111",
            "label": "red bicycle",
            "sha256": "a" * 64,
            "similarity": 0.94,
        }])
        self.execute = AsyncMock(return_value="DELETE 1")

    async def __aenter__(self): return self
    async def __aexit__(self, *args): return False


class Pool:
    def __init__(self): self.connection = Connection()
    def acquire(self): return self.connection


@pytest.fixture
def app(monkeypatch):
    application = FastAPI()
    application.include_router(visual_search.router)
    application.state.database_pool = Pool()
    application.state.visual_embedding_provider = SimpleNamespace(
        model="vision-embed-v1",
        embed=AsyncMock(return_value=[0.1, 0.2, 0.3]),
    )
    application.dependency_overrides[commercial_api.require_api_key] = lambda: {
        "api_key_id": "00000000-0000-0000-0000-000000000001",
        "owner_id": "account-a",
        "plan_code": "starter",
    }
    monkeypatch.setattr(visual_search, "record_usage", AsyncMock())
    return application


def test_index_stores_vector_metadata_not_image_bytes(app):
    response = TestClient(app).post(
        "/v1/vision/index",
        files={"file": ("bike.jpg", bytes([255, 216, 255]) + b"image", "image/jpeg")},
        data={"label": "red bicycle"},
    )
    assert response.status_code == 201
    assert response.json()["storage"] == "embedding_only"
    assert response.json()["raw_image_persisted"] is False
    args = app.state.database_pool.connection.fetchrow.await_args.args
    assert args[1] == "account-a"
    assert args[1] == "red bicycle"


def test_similarity_search_is_owner_scoped(app):
    response = TestClient(app).post(
        "/v1/vision/search",
        files={"file": ("query.jpg", bytes([255, 216, 255]) + b"image", "image/jpeg")},
    )
    assert response.status_code == 200
    assert response.json()["results"][0]["similarity"] == 0.94
    args = app.state.database_pool.connection.fetch.await_args.args
    assert args[2] == "account-a"
    assert args[3] == "vision-embed-v1"


def test_visual_embedding_provider_requires_https():
    with pytest.raises(ValueError):
        visual_search.VisualEmbeddingProvider("http://localhost/embed", None, "m", 3)


def test_visual_embedding_dimensions_are_bounded():
    with pytest.raises(ValueError):
        visual_search.VisualEmbeddingProvider("https://example.com/embed", None, "m", 0)
