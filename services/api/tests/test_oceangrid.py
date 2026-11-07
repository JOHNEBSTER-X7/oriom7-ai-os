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


def test_source_catalogue_lists_independent_provider_families(app):
    response = TestClient(app).get("/v1/oceangrid/sources")
    assert response.status_code == 200
    body = response.json()
    source_ids = {item["id"] for item in body["sources"]}
    assert {"copernicus_marine", "sentinel_eumetsat", "nasa_swot", "noaa", "argo", "commercial_imagery"} <= source_ids
    assert all(item["status"] != "connected" for item in body["sources"])


def test_batch_ranking_orders_eligible_sites_and_separates_exclusions(app):
    response = TestClient(app).post("/v1/oceangrid/rank", json={
        "minimum_evidence_coverage_pct": 40,
        "sites": [
            {"site_id":"candidate-a","name":"Coast A","latitude":5,"longitude":10,
             "sea_surface_temperature_c":10,"salinity_psu":30,"current_speed_m_s":1,
             "bathymetry_confidence":"high","grid_capacity_mw":400,
             "renewable_share_pct":90,"fibre_distance_km":10,
             "protected_area_overlap":False,"environmental_screening":"clear",
             "permit_status":"confirmed","water_strategy":"waterless"},
            {"site_id":"candidate-b","name":"Coast B","latitude":-5,"longitude":20,
             "sea_surface_temperature_c":25,"grid_capacity_mw":50,
             "protected_area_overlap":False,"environmental_screening":"clear",
             "permit_status":"not_started","water_strategy":"freshwater"},
            {"site_id":"candidate-c","name":"Protected coast","latitude":-10,"longitude":30,
             "protected_area_overlap":True},
        ],
    })
    assert response.status_code == 200
    body = response.json()
    assert body["ranking_scope"] == "submitted_candidates_only"
    assert body["global_coverage"] is False
    assert body["ranked_count"] == 2
    assert body["ranked_sites"][0]["site_id"] == "candidate-a"
    assert body["excluded_sites"][0]["site_id"] == "candidate-c"
    assert body["excluded_sites"][0]["ranking_reason"] == "environmental_exclusion_review"
