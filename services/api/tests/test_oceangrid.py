from unittest.mock import AsyncMock

import commercial_api
import oceangrid
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def app(monkeypatch):
    application = FastAPI()
    application.include_router(oceangrid.router)
    application.dependency_overrides[commercial_api.require_api_key] = lambda: {
        "api_key_id": "00000000-0000-0000-0000-000000000001",
        "owner_id": "account-a", "plan_code": "starter",
    }
    monkeypatch.setattr(oceangrid, "record_usage", AsyncMock())
    return application


def test_assessment_scores_known_factors_and_reports_coverage():
    body = oceangrid.SiteAssessmentRequest(
        site_id="pilot-001", name="Example coast", latitude=12, longitude=45,
        sea_surface_temperature_c=18, grid_capacity_mw=250,
        protected_area_overlap=False, environmental_screening="clear",
        permit_status="not_started", water_strategy="waterless",
    )
    result = oceangrid.assess_site(body)
    assert result["screening_score"] is not None
    assert result["evidence_coverage_pct"] < 100
    assert result["factors"]["salinity_corrosion"]["score"] is None
    assert result["screening_status"] == "insufficient_evidence"


def test_protected_area_is_flagged_for_exclusion_review():
    body = oceangrid.SiteAssessmentRequest(
        site_id="reef-1", name="Protected coast", latitude=-10, longitude=120,
        protected_area_overlap=True,
    )
    result = oceangrid.assess_site(body)
    assert result["screening_status"] == "environmental_exclusion_review"
    assert result["factors"]["environmental_constraints"]["score"] == 0.0


def test_assess_endpoint_records_usage(app):
    response = TestClient(app).post("/v1/oceangrid/assess", json={
        "site_id": "pilot-002", "name": "Test site", "latitude": 10, "longitude": 20,
        "water_strategy": "closed_loop_seawater_heat_exchanger", "permit_status": "in_progress",
    })
    assert response.status_code == 200
    assert response.json()["screening_status"] == "insufficient_evidence"
    oceangrid.record_usage.assert_awaited_once()
    assert oceangrid.record_usage.await_args.args[2] == "oceangrid"


def test_readiness_reports_unconnected_sources(app):
    response = TestClient(app).get("/v1/oceangrid/readiness")
    assert response.status_code == 200
    assert response.json()["live_data_ingestion"] == "not_configured"
    assert response.json()["providers"]["copernicus_marine"] == "not_connected"


def test_coordinates_are_validated():
    with pytest.raises(Exception):
        oceangrid.SiteAssessmentRequest(site_id="bad", name="Invalid", latitude=91, longitude=0)
