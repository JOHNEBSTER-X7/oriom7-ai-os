from fastapi import FastAPI
from fastapi.testclient import TestClient

from accessibility import MemoryProfileStore, router


def build_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.state.accessibility_profile_store = MemoryProfileStore()

    @app.middleware("http")
    async def test_identity(request, call_next):
        request.state.user_id = request.headers.get("X-Test-User")
        return await call_next(request)

    return TestClient(app)


def test_profile_requires_authenticated_identity():
    client = build_client()
    response = client.get("/v1/accessibility/profile")
    assert response.status_code == 401


def test_profile_lifecycle_and_user_isolation():
    client = build_client()
    alice = {"X-Test-User": "alice"}
    bob = {"X-Test-User": "bob"}

    initial = client.get("/v1/accessibility/profile", headers=alice)
    assert initial.status_code == 200
    assert initial.json()["saved"] is False
    assert initial.json()["profile"]["interaction"]["voiceNavigation"] is False

    profile = initial.json()["profile"]
    profile["display"]["textScale"] = 1.6
    profile["interaction"]["voiceNavigation"] = True
    saved = client.put("/v1/accessibility/profile", headers=alice, json=profile)
    assert saved.status_code == 200
    assert saved.json()["profile"]["display"]["textScale"] == 1.6
    assert saved.json()["profile"]["interaction"]["voiceNavigation"] is True

    assert client.get("/v1/accessibility/profile", headers=bob).json()["saved"] is False
    assert client.get("/v1/accessibility/profile", headers=alice).json()["profile"]["display"]["textScale"] == 1.6

    deleted = client.delete("/v1/accessibility/profile", headers=alice)
    assert deleted.status_code == 204
    assert client.get("/v1/accessibility/profile", headers=alice).json()["saved"] is False


def test_invalid_and_diagnostic_fields_are_rejected():
    client = build_client()
    headers = {"X-Test-User": "alice"}
    profile = client.get("/v1/accessibility/profile", headers=headers).json()["profile"]
    profile["diagnosis"] = "not allowed"
    response = client.put("/v1/accessibility/profile", headers=headers, json=profile)
    assert response.status_code == 422


def test_resolve_does_not_persist_temporary_override():
    client = build_client()
    headers = {"X-Test-User": "alice"}
    response = client.post(
        "/v1/accessibility/resolve",
        headers=headers,
        json={"overrides": {"display": {"textScale": 1.8}, "content": {"preserveCitations": False}}},
    )
    assert response.status_code == 200
    assert response.json()["profile"]["display"]["textScale"] == 1.8
    assert response.json()["profile"]["content"]["preserveCitations"] is True
    saved = client.get("/v1/accessibility/profile", headers=headers)
    assert saved.json()["profile"]["display"]["textScale"] == 1
