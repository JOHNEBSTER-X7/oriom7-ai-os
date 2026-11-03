"""ORIOM7 accessibility profile API.

Profiles contain user-selected functional preferences only. Authentication must be
provided by trusted middleware; arbitrary user IDs are never accepted from clients.
"""
from __future__ import annotations

import json
import os
from typing import Any, Literal, Protocol

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError

router = APIRouter(prefix="/v1/accessibility", tags=["accessibility"])


class DisplayPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    textScale: float = Field(default=1, ge=0.8, le=2.5)
    fontFamily: str = Field(default="system", pattern="^(system|sans|serif|dyslexia_friendly)$")
    fontWeight: str = Field(default="normal", pattern="^(normal|medium|bold)$")
    lineHeight: float = Field(default=1.5, ge=1.2, le=2.2)
    letterSpacing: float = Field(default=0, ge=0, le=0.12)
    contrast: str = Field(default="system", pattern="^(system|standard|high|more)$")
    theme: str = Field(default="system", pattern="^(system|light|dark|warm)$")
    readingGuide: bool = False


class ReadingPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    speechOutput: bool = False
    speechRate: float = Field(default=1, ge=0.6, le=1.8)
    highlightSpokenText: bool = False
    plainLanguage: bool = False
    detailLevel: str = Field(default="balanced", pattern="^(concise|balanced|detailed)$")
    preferredLanguage: str | None = Field(default=None, min_length=2, max_length=35)


class InteractionPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    voiceInput: bool = False
    voiceNavigation: bool = False
    largeTargets: bool = False
    keyboardFirst: bool = False
    showFocus: bool = True
    confirmDestructiveActions: bool = True
    saveProgress: bool = False


class ContentPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reduceClutter: bool = False
    stepByStep: bool = False
    showShortAnswerFirst: bool = True
    preserveCitations: Literal[True] = True


class SensoryPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reduceMotion: bool = False
    disableAutoplay: bool = True
    muteNonessentialAudio: bool = False
    calmPresentation: bool = False


class AccessibilityProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(default=1, ge=1, le=1)
    display: DisplayPreferences = Field(default_factory=DisplayPreferences)
    reading: ReadingPreferences = Field(default_factory=ReadingPreferences)
    interaction: InteractionPreferences = Field(default_factory=InteractionPreferences)
    content: ContentPreferences = Field(default_factory=ContentPreferences)
    sensory: SensoryPreferences = Field(default_factory=SensoryPreferences)


class ResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    overrides: dict[str, Any] = Field(default_factory=dict)


class ProfileStore(Protocol):
    async def get(self, subject: str) -> dict[str, Any] | None: ...
    async def put(self, subject: str, profile: dict[str, Any]) -> None: ...
    async def delete(self, subject: str) -> None: ...


class MemoryProfileStore:
    """Development/test adapter only. Data is lost when the process restarts."""
    def __init__(self) -> None:
        self._profiles: dict[str, dict[str, Any]] = {}

    async def get(self, subject: str) -> dict[str, Any] | None:
        return self._profiles.get(subject)

    async def put(self, subject: str, profile: dict[str, Any]) -> None:
        self._profiles[subject] = profile

    async def delete(self, subject: str) -> None:
        self._profiles.pop(subject, None)


class PostgresProfileStore:
    """PostgreSQL adapter using asyncpg; table is provisioned by the SQL migration."""
    def __init__(self, pool: Any) -> None:
        self.pool = pool

    async def get(self, subject: str) -> dict[str, Any] | None:
        async with self.pool.acquire() as connection:
            row = await connection.fetchrow(
                "SELECT profile FROM accessibility_profiles WHERE subject_id = $1",
                subject,
            )
        if row is None:
            return None
        value = row["profile"]
        return json.loads(value) if isinstance(value, str) else value

    async def put(self, subject: str, profile: dict[str, Any]) -> None:
        async with self.pool.acquire() as connection:
            await connection.execute(
                """INSERT INTO accessibility_profiles (subject_id, profile, updated_at)
                   VALUES ($1, $2::jsonb, now())
                   ON CONFLICT (subject_id) DO UPDATE
                   SET profile = EXCLUDED.profile, updated_at = now()""",
                subject,
                json.dumps(profile),
            )

    async def delete(self, subject: str) -> None:
        async with self.pool.acquire() as connection:
            await connection.execute(
                "DELETE FROM accessibility_profiles WHERE subject_id = $1",
                subject,
            )


async def authenticated_subject(request: Request) -> str:
    """Read identity only from trusted auth middleware.

    The development header is disabled unless explicitly enabled. Production identity
    must be verified by the deployment's OIDC/session middleware before this runs.
    """
    subject = getattr(request.state, "user_id", None)
    if not subject and os.getenv("ORIOM7_ALLOW_DEV_USER_HEADER") == "true":
        subject = request.headers.get("X-ORIOM7-DEV-USER")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "authentication_required", "message": "Sign in to manage a saved accessibility profile."},
        )
    return str(subject)


def get_store(request: Request) -> ProfileStore:
    store = getattr(request.app.state, "accessibility_profile_store", None)
    if store is None:
        raise HTTPException(status_code=503, detail="Accessibility profile storage is unavailable.")
    return store


def default_profile() -> dict[str, Any]:
    return AccessibilityProfile().model_dump(mode="json")


def merge_profile(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Deep merge allow-listed overrides; Pydantic then validates the complete result."""
    merged = json.loads(json.dumps(base))
    allowed = {"display", "reading", "interaction", "content", "sensory"}
    for section, values in overrides.items():
        if section not in allowed or not isinstance(values, dict):
            raise HTTPException(status_code=422, detail=f"Invalid override section: {section}")
        merged[section].update(values)
    merged["content"]["preserveCitations"] = True
    try:
        return AccessibilityProfile.model_validate(merged).model_dump(mode="json")
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_input=False)) from exc


@router.get("/profile")
async def get_profile(
    subject: str = Depends(authenticated_subject),
    store: ProfileStore = Depends(get_store),
) -> dict[str, Any]:
    profile = await store.get(subject)
    return {"profile": profile or default_profile(), "saved": profile is not None}


@router.put("/profile")
async def put_profile(
    profile: AccessibilityProfile,
    subject: str = Depends(authenticated_subject),
    store: ProfileStore = Depends(get_store),
) -> dict[str, Any]:
    canonical = profile.model_dump(mode="json")
    await store.put(subject, canonical)
    return {"profile": canonical, "saved": True}


@router.delete("/profile", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    subject: str = Depends(authenticated_subject),
    store: ProfileStore = Depends(get_store),
) -> Response:
    await store.delete(subject)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/resolve")
async def resolve_profile(
    payload: ResolveRequest,
    subject: str = Depends(authenticated_subject),
    store: ProfileStore = Depends(get_store),
) -> dict[str, Any]:
    """Resolve temporary overrides without persisting them."""
    base = await store.get(subject) or default_profile()
    return {"profile": merge_profile(base, payload.overrides), "saved": False}
