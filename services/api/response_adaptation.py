"""Accessibility-aware response presentation contract.

This module produces structured, model-provider-neutral instructions. It does not
rewrite answers, translate content, synthesize speech or call an AI provider.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from accessibility import (
    ProfileStore,
    authenticated_subject,
    default_profile,
    get_store,
    merge_profile,
)

router = APIRouter(prefix="/v1/assistant", tags=["assistant-accessibility"])


class PresentationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    overrides: dict[str, Any] = Field(default_factory=dict)


def build_response_presentation(profile: dict[str, Any]) -> dict[str, Any]:
    """Convert a validated accessibility profile into explicit output directives."""
    reading = profile["reading"]
    content = profile["content"]
    sensory = profile["sensory"]

    return {
        "language": reading.get("preferredLanguage") or "auto",
        "language_source": "user_preference" if reading.get("preferredLanguage") else "automatic_detection",
        "plain_language": reading["plainLanguage"],
        "detail_level": reading["detailLevel"],
        "short_answer_first": content["showShortAnswerFirst"],
        "step_by_step": content["stepByStep"],
        "reduced_content_density": content["reduceClutter"],
        "preserve_citations": True,
        "preserve_uncertainty": True,
        "preserve_safety_warnings": True,
        "speech_output_requested": reading["speechOutput"],
        "speech_rate": reading["speechRate"],
        "highlight_spoken_text": reading["highlightSpokenText"],
        "calm_presentation": sensory["calmPresentation"],
        "provider_execution": "not_connected",
    }


@router.post("/presentation")
async def assistant_presentation(
    payload: PresentationRequest,
    subject: str = Depends(authenticated_subject),
    store: ProfileStore = Depends(get_store),
) -> dict[str, Any]:
    """Return the user's response-formatting directives without invoking a model."""
    saved = await store.get(subject) or default_profile()
    resolved = merge_profile(saved, payload.overrides)
    return {
        "presentation": build_response_presentation(resolved),
        "profile_saved": await store.get(subject) is not None,
        "overrides_persisted": False,
        "status": "ready_for_orchestrator",
    }
