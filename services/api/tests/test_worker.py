from fastapi import FastAPI
from fastapi.testclient import TestClient

from ingestion import router
from worker import permanent_failure, retry_delay_seconds


def test_retry_delay_is_exponential_and_bounded():
    assert retry_delay_seconds(1) == 30
    assert retry_delay_seconds(2) == 60
    assert retry_delay_seconds(3) == 120
    assert retry_delay_seconds(20) == 21600


def test_permanent_failure_classification():
    assert permanent_failure(403)
    assert permanent_failure(404)
    assert permanent_failure(415)
    assert not permanent_failure(429)
    assert not permanent_failure(503)


def test_queue_endpoint_requires_ingestion_token(monkeypatch):
    monkeypatch.setenv("ORIOM7_INGESTION_TOKEN", "test-secret")
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).post(
        "/v1/ingestion/queue",
        json={"url": "https://example.org/page", "language": "en"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "ingestion_unauthorised"
