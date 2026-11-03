import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ingestion import PageText, SourceRegistration, router


def test_html_extractor_ignores_scripts_and_styles():
    parser = PageText()
    parser.feed("<html><title>Battery report</title><body><p>Useful evidence text.</p><script>secret()</script><style>.x{}</style></body></html>")
    assert parser.title == "Battery report"
    assert "Useful evidence text." in parser.text
    assert "secret" not in parser.text
    assert ".x" not in parser.text


def test_source_registration_requires_https():
    with pytest.raises(ValueError):
        SourceRegistration(
            base_url="http://example.org",
            rights_basis="Licensed content",
            approval_reference="LIC-123",
            approved_by="operator",
        )


def test_source_registration_normalises_origin_and_path():
    source = SourceRegistration(
        base_url="https://Example.org/research/",
        rights_basis="Publisher licence",
        approval_reference="LIC-123",
        approved_by="operator",
    )
    assert source.base_url == "https://example.org/research"


def test_ingestion_routes_require_secret_token(monkeypatch):
    monkeypatch.setenv("ORIOM7_INGESTION_TOKEN", "test-secret")
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).post(
        "/v1/ingestion/sources",
        json={
            "base_url": "https://example.org",
            "rights_basis": "Licensed content",
            "approval_reference": "LIC-123",
            "approved_by": "operator",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "ingestion_unauthorised"
