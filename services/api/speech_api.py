"""Provider-backed speech recognition and synthesis APIs.

Audio is bounded in memory and forwarded only to operator-configured HTTPS
providers. ORIOM7 does not persist uploaded or generated audio.
"""
from __future__ import annotations

import json
import os
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from commercial_api import record_usage, require_api_key

router = APIRouter(tags=["speech-intelligence"])
MAX_AUDIO_BYTES = 25 * 1024 * 1024
MAX_OUTPUT_BYTES = 20 * 1024 * 1024
MAX_DURATION_SECONDS = 24 * 60 * 60
AUDIO_SIGNATURES = {
    "audio/wav": (b"RIFF",), "audio/x-wav": (b"RIFF",),
    "audio/mpeg": (b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"),
    "audio/ogg": (b"OggS",), "audio/webm": (b"\x1aE\xdf\xa3",),
    "audio/mp4": (b"\x00\x00\x00",), "audio/aac": (b"\xff\xf1", b"\xff\xf9"),
}
OUTPUT_TYPES = {"audio/mpeg", "audio/wav", "audio/ogg", "audio/webm", "audio/mp4"}


def _trusted_endpoint(endpoint: str) -> None:
    parsed = urlparse(endpoint)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("Speech provider endpoint must be a trusted HTTPS URL")


class SpeechRecognitionProvider:
    def __init__(self, endpoint: str, api_key: str | None, timeout: float = 90.0):
        _trusted_endpoint(endpoint)
        self.endpoint, self.api_key, self.timeout = endpoint, api_key, timeout

    async def transcribe(self, content: bytes, filename: str, media_type: str, language: str):
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False) as client:
            async with client.stream("POST", self.endpoint, headers=headers,
                files={"file": (filename, content, media_type)}, data={"language": language}) as response:
                response.raise_for_status()
                chunks, size = [], 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > 3 * 1024 * 1024:
                        raise ValueError("Speech provider response exceeded limit")
                    chunks.append(chunk)
        payload = json.loads(b"".join(chunks).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Speech provider response must be an object")
        text, duration = payload.get("text"), payload.get("duration_seconds")
        if not isinstance(text, str) or not text.strip() or len(text) > 1_000_000:
            raise ValueError("Speech provider returned invalid transcript text")
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not 0 < duration <= MAX_DURATION_SECONDS:
            raise ValueError("Speech provider returned invalid duration_seconds")
        language_result = payload.get("language", language)
        if not isinstance(language_result, str) or len(language_result) > 35:
            raise ValueError("Speech provider returned invalid language")
        segments = payload.get("segments", [])
        if not isinstance(segments, list) or len(segments) > 10000:
            raise ValueError("Speech provider returned invalid segments")
        clean_segments = []
        for segment in segments:
            if not isinstance(segment, dict):
                raise ValueError("Speech provider returned invalid segment")
            start, end, segment_text = segment.get("start"), segment.get("end"), segment.get("text")
            if (isinstance(start, bool) or not isinstance(start, (int, float))
                or isinstance(end, bool) or not isinstance(end, (int, float))
                or start < 0 or end < start or end > duration
                or not isinstance(segment_text, str) or len(segment_text) > 10000):
                raise ValueError("Speech provider returned invalid segment")
            item = {"start": float(start), "end": float(end), "text": segment_text}
            speaker = segment.get("speaker")
            if speaker is not None:
                if not isinstance(speaker, str) or len(speaker) > 80:
                    raise ValueError("Speech provider returned invalid speaker label")
                item["speaker"] = speaker
            clean_segments.append(item)
        return text, float(duration), language_result, clean_segments


class TextToSpeechProvider:
    def __init__(self, endpoint: str, api_key: str | None, timeout: float = 90.0):
        _trusted_endpoint(endpoint)
        self.endpoint, self.api_key, self.timeout = endpoint, api_key, timeout

    async def synthesize(self, text: str, voice: str, audio_format: str):
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False) as client:
            async with client.stream("POST", self.endpoint, headers=headers,
                json={"text": text, "voice": voice, "format": audio_format}) as response:
                response.raise_for_status()
                media_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                if media_type not in OUTPUT_TYPES:
                    raise ValueError("Speech synthesis provider returned unsupported audio type")
                chunks, size = [], 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > MAX_OUTPUT_BYTES:
                        raise ValueError("Speech synthesis output exceeded limit")
                    chunks.append(chunk)
        audio = b"".join(chunks)
        if not audio:
            raise ValueError("Speech synthesis provider returned empty audio")
        return audio, media_type


def build_speech_provider_from_env():
    endpoint = os.getenv("ORIOM7_SPEECH_ENDPOINT")
    return SpeechRecognitionProvider(endpoint, os.getenv("ORIOM7_SPEECH_API_KEY")) if endpoint else None


def build_tts_provider_from_env():
    endpoint = os.getenv("ORIOM7_TTS_ENDPOINT")
    return TextToSpeechProvider(endpoint, os.getenv("ORIOM7_TTS_API_KEY")) if endpoint else None


def validate_audio(content: bytes, media_type: str) -> str:
    signatures = AUDIO_SIGNATURES.get(media_type)
    if not content:
        raise HTTPException(status_code=422, detail="Uploaded audio is empty")
    if signatures is None or not any(content.startswith(signature) for signature in signatures):
        raise HTTPException(status_code=415, detail="Unsupported audio type or invalid audio signature")
    return {
        "audio/wav": "wav", "audio/x-wav": "wav", "audio/mpeg": "mp3",
        "audio/ogg": "ogg", "audio/webm": "webm", "audio/mp4": "m4a", "audio/aac": "aac",
    }[media_type]


class SpeechSynthesisRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    voice: str = Field(default="default", min_length=1, max_length=80)
    format: str = Field(default="mp3", pattern="^(mp3|wav|ogg|webm|mp4)$")


@router.post("/v1/speech/transcriptions")
async def transcribe_audio(request: Request, file: UploadFile = File(...),
    language: str = Form(default="auto", min_length=2, max_length=35),
    key: dict = Depends(require_api_key)):
    provider = getattr(request.app.state, "speech_provider", None)
    if provider is None:
        raise HTTPException(status_code=503, detail="Speech recognition provider is not configured")
    media_type = (file.content_type or "").split(";", 1)[0].strip().lower()
    content = await file.read(MAX_AUDIO_BYTES + 1)
    if len(content) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio exceeds the 25 MB upload limit")
    extension = validate_audio(content, media_type)
    try:
        transcript, duration, detected_language, segments = await provider.transcribe(
            content, f"audio.{extension}", media_type, language)
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Speech recognition provider timed out") from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail="Speech recognition provider rejected the audio") from exc
    except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail="Speech recognition provider failed or returned invalid data") from exc
    units = max(1, int(duration + 0.999))
    await record_usage(request, key, "speech", units, 200,
        {"language": detected_language, "segments": len(segments)})
    return {"object": "speech_transcription", "text": transcript, "language": detected_language,
        "duration_seconds": duration, "segments": segments, "usage": {"audio_seconds": units},
        "storage": "not_persisted"}


@router.post("/v1/speech/synthesis")
async def synthesize_speech(body: SpeechSynthesisRequest, request: Request,
    key: dict = Depends(require_api_key)):
    provider = getattr(request.app.state, "tts_provider", None)
    if provider is None:
        raise HTTPException(status_code=503, detail="Text-to-speech provider is not configured")
    try:
        audio, media_type = await provider.synthesize(body.text, body.voice, body.format)
        if not isinstance(audio, bytes) or not audio or len(audio) > MAX_OUTPUT_BYTES or media_type not in OUTPUT_TYPES:
            raise ValueError("Speech synthesis provider returned invalid audio")
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Text-to-speech provider timed out") from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail="Text-to-speech provider rejected the request") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Text-to-speech provider failed or returned invalid audio") from exc
    await record_usage(request, key, "text_to_speech", len(body.text), 200,
        {"voice": body.voice, "format": body.format, "media_type": media_type})
    return Response(content=audio, media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="oriom7-speech.{body.format}"',
                 "Cache-Control": "no-store"})
