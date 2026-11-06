from types import SimpleNamespace
from unittest.mock import AsyncMock

import commercial_api
import ocr_api
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from ocr_api import router

@pytest.fixture
def app():
    application = FastAPI()
    application.include_router(router)
    application.state.ocr_provider = SimpleNamespace(
        extract=AsyncMock(return_value=("Invoice number 12345", 2))
    )
    application.dependency_overrides[commercial_api.require_api_key] = lambda: {
        "api_key_id": "00000000-0000-0000-0000-000000000001",
        "owner_id": "acct",
        "plan_code": "starter",
    }
    return application

def test_ocr_extracts_text_and_records_page_usage(app, monkeypatch):
    usage = AsyncMock()
    monkeypatch.setattr(ocr_api, "record_usage", usage)
    response = TestClient(app).post(
        "/v1/documents/ocr",
        files={"file": ("invoice.pdf", b"%PDF-1.7 test document", "application/pdf")},
        data={"language": "en"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["extracted_text"] == "Invoice number 12345"
    assert payload["pages"] == 2
    assert payload["storage"] == "not_persisted"
    usage.assert_awaited_once()
    assert usage.await_args.args[3] == 2

def test_ocr_rejects_mismatched_file_signature(app):
    response = TestClient(app).post(
        "/v1/documents/ocr",
        files={"file": ("invoice.pdf", b"not a pdf", "application/pdf")},
    )
    assert response.status_code == 415

def test_ocr_is_unavailable_without_configured_provider(app):
    app.state.ocr_provider = None
    response = TestClient(app).post(
        "/v1/documents/ocr",
        files={"file": ("image.png", b"\x89PNG\r\n\x1a\ncontent", "image/png")},
    )
    assert response.status_code == 503

def test_ocr_provider_requires_https():
    with pytest.raises(ValueError):
        ocr_api.OCRProvider("http://localhost/ocr", None)

def test_ocr_rejects_unsupported_media_type(app):
    response = TestClient(app).post(
        "/v1/documents/ocr",
        files={"file": ("notes.txt", b"plain text", "text/plain")},
    )
    assert response.status_code == 415
