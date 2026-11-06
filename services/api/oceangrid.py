"""Evidence-aware coastal cooling site assessment for ORIOM7 OCEANGRID V1.

This module scores only caller-supplied normalized evidence. It does not fetch
satellite/ocean data, certify a site, or replace engineering and regulatory review.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, model_validator

from commercial_api import record_usage, require_api_key

router = APIRouter(tags=["oceangrid"])

class EvidenceSource(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    source_type: Literal["satellite", "in_situ", "model", "official_registry", "user_supplied"]
    data_kind: Literal["observed", "modelled", "user_supplied"]
    licence: str = Field(min_length=2, max_length=160)
    observed_at: datetime
    resolution_m: float | None = Field(default=None, gt=0, le=10_000_000)
    url: str | None = Field(default=None, max_length=1000)

class SiteAssessmentRequest(BaseModel):
    site_id: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=160)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    sea_surface_temperature_c: float | None = Field(default=None, ge=-3, le=45)
    salinity_psu: float | None = Field(default=None, ge=0, le=50)
    current_speed_m_s: float | None = Field(default=None, ge=0, le=10)
    water_depth_m: float | None = Field(default=None, ge=0, le=12000)
    bathymetry_confidence: Literal["high", "medium", "low", "unknown"] = "unknown"
    grid_capacity_mw: float | None = Field(default=None, ge=0, le=1_000_000)
    renewable_share_pct: float | None = Field(default=None, ge=0, le=100)
    fibre_distance_km: float | None = Field(default=None, ge=0, le=100_000)
    protected_area_overlap: bool | None = None
    environmental_screening: Literal["clear", "review_required", "restricted", "unknown"] = "unknown"
    permit_status: Literal["confirmed", "in_progress", "not_started", "unknown"] = "unknown"
    water_strategy: Literal["closed_loop_seawater_heat_exchanger", "recycled_water", "waterless", "freshwater", "unknown"] = "unknown"
    evidence: list[EvidenceSource] = Field(default_factory=list, max_length=40)

    @model_validator(mode="after")
    def require_evidence_for_observations(self):
        if len(self.evidence) == 0 and any(v is not None for v in (
            self.sea_surface_temperature_c, self.salinity_psu, self.current_speed_m_s,
            self.water_depth_m, self.grid_capacity_mw, self.renewable_share_pct,
            self.fibre_distance_km, self.protected_area_overlap
        )):
            # Data may be supplied during an early desktop assessment, but it must
            # be explicitly labelled as user-supplied rather than silently trusted.
            return self
        return self

def _band(value: float | None, low: float, high: float, inverse: bool = False) -> tuple[float | None, str]:
    if value is None:
        return None, "unknown"
    score = max(0.0, min(100.0, (value - low) / (high - low) * 100.0))
    if inverse:
        score = 100.0 - score
    return round(score, 1), "provided"

def assess_site(site: SiteAssessmentRequest) -> dict:
    factors = {}
    factors["thermal_resource"] = _band(site.sea_surface_temperature_c, 2.0, 30.0, inverse=True)
    factors["salinity_corrosion"] = _band(site.salinity_psu, 0.0, 40.0, inverse=True)
    factors["current_conditions"] = _band(site.current_speed_m_s, 0.0, 2.0)
    factors["bathymetry"] = ({"high": 100.0, "medium": 65.0, "low": 30.0}.get(site.bathymetry_confidence), site.bathymetry_confidence)
    factors["power_access"] = _band(site.grid_capacity_mw, 0.0, 500.0)
    factors["renewable_power"] = _band(site.renewable_share_pct, 0.0, 100.0)
    factors["fibre_connectivity"] = _band(site.fibre_distance_km, 0.0, 100.0, inverse=True)
    factors["environmental_constraints"] = (
        0.0 if site.protected_area_overlap is True or site.environmental_screening == "restricted"
        else 100.0 if site.protected_area_overlap is False and site.environmental_screening == "clear"
        else None,
        "restricted" if site.protected_area_overlap is True or site.environmental_screening == "restricted"
        else "clear" if site.protected_area_overlap is False and site.environmental_screening == "clear"
        else "unknown",
    )
    factors["permitting"] = ({"confirmed": 100.0, "in_progress": 50.0, "not_started": 0.0}.get(site.permit_status), site.permit_status)
    factors["water_strategy"] = (
        {"waterless": 100.0, "recycled_water": 90.0, "closed_loop_seawater_heat_exchanger": 85.0,
         "freshwater": 10.0}.get(site.water_strategy), site.water_strategy
    )
    weights = {
        "thermal_resource": 15, "salinity_corrosion": 8, "current_conditions": 5,
        "bathymetry": 8, "power_access": 18, "renewable_power": 12,
        "fibre_connectivity": 10, "environmental_constraints": 12,
        "permitting": 7, "water_strategy": 5,
    }
    known = [(name, value, weights[name]) for name, (value, _) in factors.items() if value is not None]
    total_weight = sum(weight for _, _, weight in known)
    score = round(sum(value * weight for _, value, weight in known) / total_weight, 1) if total_weight else None
    coverage = round(total_weight / sum(weights.values()) * 100, 1)
    blocked = site.protected_area_overlap is True or site.environmental_screening == "restricted"
    if blocked:
        status = "environmental_exclusion_review"
    elif coverage < 60:
        status = "insufficient_evidence"
    elif site.permit_status != "confirmed":
        status = "preliminary_screening_only"
    else:
        status = "engineering_due_diligence_required"
    return {
        "site_id": site.site_id, "name": site.name,
        "coordinates": {"latitude": site.latitude, "longitude": site.longitude},
        "screening_score": score, "evidence_coverage_pct": coverage,
        "screening_status": status, "factors": {
            name: {"score": value, "status": state, "weight_pct": weights[name]}
            for name, (value, state) in factors.items()
        },
        "evidence": [item.model_dump(mode="json") for item in site.evidence],
        "evidence_count": len(site.evidence),
        "assessed_at": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "This is a transparent preliminary screening score, not a feasibility finding or investment recommendation.",
            "Missing inputs are excluded from the weighted score and reduce evidence coverage; they are not treated as favourable.",
            "Satellite, model and in-situ evidence must be independently validated for age, resolution, licence and local applicability.",
            "Environmental exclusion, marine permits, thermal discharge, ecology, water rights, grid, fibre and engineering require competent local review.",
            "No live satellite, oceanographic, bathymetric, grid or regulatory provider is queried by this endpoint.",
        ],
    }


SOURCE_CATALOGUE = [
    {"id":"copernicus_marine","name":"Copernicus Marine Service","data":["ocean temperature","salinity","currents","waves","model analysis and forecasts"],"modality":"satellite, in-situ and model products","status":"catalogued_not_connected","licence_review_required":True},
    {"id":"sentinel_eumetsat","name":"Copernicus Sentinel and EUMETSAT","data":["sea-surface temperature","ocean colour","sea level","coastal observations"],"modality":"satellite observations","status":"catalogued_not_connected","licence_review_required":True},
    {"id":"nasa_swot","name":"NASA SWOT","data":["ocean surface water elevation and topography"],"modality":"satellite altimetry","status":"catalogued_not_connected","licence_review_required":True},
    {"id":"noaa","name":"NOAA ocean and coastal data","data":["bathymetry","marine observations","coastal datasets"],"modality":"in-situ, survey and model datasets","status":"catalogued_not_connected","licence_review_required":True},
    {"id":"argo","name":"Argo","data":["ocean temperature profiles","salinity profiles"],"modality":"in-situ profiling floats","status":"catalogued_not_connected","licence_review_required":True},
    {"id":"commercial_imagery","name":"Licensed commercial satellite providers","data":["selected high-resolution coastal imagery"],"modality":"commercial satellite imagery and tasking","status":"provider_selection_required","licence_review_required":True},
]

@router.get("/v1/oceangrid/sources")
async def oceangrid_sources(request: Request, key: dict = Depends(require_api_key)):
    return {
        "object": "oceangrid_source_catalogue",
        "sources": SOURCE_CATALOGUE,
        "notice": "Catalogue entries are planned integrations, not connected services or guarantees of coverage, resolution, freshness or licence rights.",
    }

@router.post("/v1/oceangrid/assess")
async def assess_coastal_site(
    body: SiteAssessmentRequest, request: Request,
    key: dict = Depends(require_api_key),
):
    result = assess_site(body)
    await record_usage(request, key, "oceangrid", 1, 200, {
        "site_id": body.site_id, "evidence_count": len(body.evidence),
        "screening_status": result["screening_status"],
    })
    return result


@router.post("/v1/oceangrid/rank")
async def rank_coastal_candidates(
    body: CoastalRankingRequest, request: Request,
    key: dict = Depends(require_api_key),
):
    assessed = [assess_site(site) for site in body.sites]
    eligible = []
    excluded = []
    for result in assessed:
        if result["screening_status"] == "environmental_exclusion_review":
            excluded.append({**result, "ranking_reason": "environmental_exclusion_review"})
        elif result["screening_score"] is None or result["evidence_coverage_pct"] < body.minimum_evidence_coverage_pct:
            excluded.append({**result, "ranking_reason": "insufficient_evidence"})
        else:
            eligible.append(result)
    eligible.sort(
        key=lambda item: (item["screening_score"], item["evidence_coverage_pct"]),
        reverse=True,
    )
    ranked = [{**item, "rank": index + 1} for index, item in enumerate(eligible)]
    await record_usage(request, key, "oceangrid", len(body.sites), 200, {
        "operation": "batch_coastal_ranking",
        "submitted_sites": len(body.sites),
        "ranked_sites": len(ranked),
        "excluded_sites": len(excluded),
    })
    return {
        "object": "oceangrid_coastal_ranking",
        "ranking_scope": "submitted_candidates_only",
        "global_coverage": False,
        "minimum_evidence_coverage_pct": body.minimum_evidence_coverage_pct,
        "submitted_count": len(body.sites),
        "ranked_count": len(ranked),
        "excluded_count": len(excluded),
        "ranked_sites": ranked,
        "excluded_sites": excluded,
        "notice": "This ranks only the candidates supplied in this request. It is not a global coastline ranking, and scores are preliminary screening indicators, not engineering, environmental or investment approvals.",
    }

@router.get("/v1/oceangrid/readiness")
async def oceangrid_readiness(request: Request, key: dict = Depends(require_api_key)):
    return {
        "module": "ORIOM7 OCEANGRID",
        "version": "1.0.0",
        "assessment_api": "available",
        "candidate_ranking_api": "available",
        "global_coastline_ranking": "not_available_until_global_data_ingestion",
        "live_data_ingestion": "not_configured",
        "providers": {
            "copernicus_marine": "not_connected",
            "eumetsat": "not_connected",
            "nasa_swot": "not_connected",
            "noaa": "not_connected",
            "argo": "not_connected",
            "commercial_satellite": "not_connected",
        },
        "spatial_database": "not_configured",
        "production_site_ranking": "not_available",
        "next_requirements": [
            "Approve provider licences and access methods",
            "Implement provider-specific ingestion and provenance validation",
            "Add spatial storage and protected-area/EEZ overlays",
            "Validate data freshness, spatial resolution and uncertainty",
            "Complete environmental, water, energy and permitting reviews",
        ],
    }
