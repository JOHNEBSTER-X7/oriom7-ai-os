from fastapi import FastAPI
from fastapi.testclient import TestClient

from accessibility import MemoryProfileStore, router as accessibility_router
from response_adaptation import build_response_presentation, router as assistant_router


def build_client() -> TestClient:
    app = FastAPI()
    app.include_router(accessibility_router)
    app.include_router(assistant_router)
    app.state.accessibility_profile_store = MemoryProfileStore()

    @app.middleware("http")
    async def test_identity(request, call_next):
        request.state.user_id = request.headers.get("X-Test-User")
        return await call_next(request)

    return TestClient(app)


def test_presentation_requires_authenticated_identity():
    response = build_client().post("/v1/assistant/presentation", json={})
    assert response.status_code == 401


def test_presentation_uses_saved_accessibility_preferences():
    client = build_client()
    headers = {"X-Test-User": "alice"}
    profile_response = client.get("/v1/accessibility/profile", headers=headers)
    profile = profile_response.json()["profile"]
    profile["reading"]["plainLanguage"] = True
    profile["reading"]["detailLevel"] = "concise"
    profile["reading"]["preferredLanguage"] = "en-GB"
    profile["content"]["stepByStep"] = True
    profile["reading"]["speechOutput"] = True
    client.put("/v1/accessibility/profile", headers=headers, json=profile)

    response = client.post("/v1/assistant/presentation", headers=headers, json={})
    assert response.status_code == 200
    data = response.json()
    presentation = data["presentation"]
    assert data["status"] == "ready_for_orchestrator"
    assert data["profile_saved"] is True
    assert presentation["language"] == "en-GB"
    assert presentation["plain_language"] is True
    assert presentation["detail_level"] == "concise"
    assert presentation["step_by_step"] is True
    assert presentation["speech_output_requested"] is True
    assert presentation["preserve_citations"] is True
    assert presentation["preserve_uncertainty"] is True
    assert presentation["preserve_safety_warnings"] is True


def test_temporary_presentation_overrides_are_not_persisted():
    client = build_client()
    headers = {"X-Test-User": "alice"}
    response = client.post(
        "/v1/assistant/presentation",
        headers=headers,
        json={"overrides": {"reading": {"plainLanguage": True, "detailLevel": "concise"}}},
    )
    assert response.status_code == 200
    assert response.json()["presentation"]["plain_language"] is True
    assert response.json()["presentation"]["detail_level"] == "concise"
    assert response.json()["overrides_persisted"] is False

    saved = client.get("/v1/accessibility/profile", headers=headers).json()["profile"]
    assert saved["reading"]["plainLanguage"] is False
    assert saved["reading"]["detailLevel"] == "balanced"


def test_presentation_cannot_disable_citations_or_safety_preservation():
    profile = {
        "reading": {
            "plainLanguage": True,
            "detailLevel": "concise",
            "preferredLanguage": None,
            "speechOutput": False,
            "speechRate": 1.0,
            "highlightSpokenText": False,
        },
        "content": {
            "showShortAnswerFirst": True,
            "stepByStep": False,
            "reduceClutter": False,
        },
        "sensory": {"calmPresentation": False},
    }
    result = build_response_presentation(profile)
    assert result["preserve_citations"] is True
    assert result["preserve_uncertainty"] is True
    assert result["preserve_safety_warnings"] is True
    assert result["language_source"] == "unspecified"
