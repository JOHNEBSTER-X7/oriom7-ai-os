"""Authenticated assistant generation endpoint."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from accessibility import ProfileStore, authenticated_subject, default_profile, get_store
from model_orchestration import ModelOrchestrator, ProviderUnavailable
from response_adaptation import build_response_presentation

router = APIRouter(prefix="/v1/assistant", tags=["assistant"])


class AssistantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    input: str = Field(min_length=1, max_length=12000)
    mode: str = Field(default="chat", pattern="^(chat|research|coding|business|education)$")
    max_output_tokens: int = Field(default=1200, ge=64, le=8192)


def build_instructions(mode: str, presentation: dict[str, Any]) -> str:
    modes = {
        "chat": "Answer conversationally and directly.",
        "research": "Separate facts, interpretation and unknowns. Never invent sources.",
        "coding": "Prioritise secure, correct and maintainable code.",
        "business": "State assumptions and distinguish estimates from verified facts.",
        "education": "Teach clearly and define unfamiliar terms.",
    }
    return (
        "You are the ORIOM7 assistant. Follow the user's request and presentation preferences. "
        "Never invent citations, quotations, evidence or URLs. If no source material is supplied, "
        "state that claims have not been independently verified. Preserve uncertainty and relevant "
        "safety warnings. Do not reveal private reasoning. "
        f"Mode: {mode}. {modes[mode]} "
        f"Language: {presentation['language']}. Plain language: {presentation['plain_language']}. "
        f"Detail: {presentation['detail_level']}. Short answer first: {presentation['short_answer_first']}. "
        f"Step by step: {presentation['step_by_step']}. Reduced content density: {presentation['reduced_content_density']}. "
        "Keep citations attached to the claims they support whenever source material is provided."
    )


@router.post("/responses")
async def create_response(
    payload: AssistantRequest,
    request: Request,
    subject: str = Depends(authenticated_subject),
    store: ProfileStore = Depends(get_store),
) -> dict[str, Any]:
    orchestrator: ModelOrchestrator | None = getattr(request.app.state, "model_orchestrator", None)
    if orchestrator is None or not orchestrator.providers:
        raise HTTPException(status_code=503, detail={
            "code": "model_providers_not_configured", "message": "No model provider is configured."
        })

    profile = await store.get(subject) or default_profile()
    presentation = build_response_presentation(profile)
    try:
        result, fallback_used = await orchestrator.generate(
            payload.input, build_instructions(payload.mode, presentation), payload.max_output_tokens
        )
    except ProviderUnavailable:
        raise HTTPException(status_code=502, detail={
            "code": "model_providers_unavailable", "message": "All configured model providers are unavailable."
        })

    return {
        "id": str(uuid.uuid4()),
        "status": "completed",
        "output_text": result.text,
        "model": {"provider": result.provider, "name": result.model, "fallback_used": fallback_used},
        "usage": {
            "input_tokens": result.input_tokens, "output_tokens": result.output_tokens,
            "total_tokens": result.total_tokens, "estimated_cost_usd": result.estimated_cost_usd,
        },
        "grounding": {"status": "not_connected", "sources": []},
        "presentation": presentation,
        "provider_request_id": result.provider_request_id,
    }

catalog_router = APIRouter(prefix="/v1", tags=["models"])


@catalog_router.get("/models")
async def list_models(
    request: Request,
    subject: str = Depends(authenticated_subject),
) -> dict[str, Any]:
    """List only configured models; never expose credentials or provider settings."""
    orchestrator: ModelOrchestrator | None = getattr(request.app.state, "model_orchestrator", None)
    providers = orchestrator.providers if orchestrator else []
    return {
        "models": [
            {
                "provider": provider.name,
                "id": provider.model,
                "capabilities": {
                    "text_generation": True,
                    "streaming": False,
                    "tool_execution": False,
                    "vision": False,
                },
            }
            for provider in providers
        ]
    }
