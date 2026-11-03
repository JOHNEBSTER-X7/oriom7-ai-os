"""Provider-neutral model adapters and fallback orchestration."""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

logger = logging.getLogger("oriom7.models")


@dataclass(frozen=True)
class ModelResult:
    provider: str
    model: str
    text: str
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    estimated_cost_usd: float | None
    provider_request_id: str | None


class ModelProvider(Protocol):
    name: str
    model: str

    async def generate(self, prompt: str, instructions: str, max_output_tokens: int) -> ModelResult: ...


class ProviderUnavailable(Exception):
    pass


class ResponsesAPIProvider:
    """Adapter for the OpenAI Responses API-compatible provider contract."""

    def __init__(self, name: str, base_url: str, api_key: str, model: str,
                 input_rate: float | None = None, output_rate: float | None = None):
        self.name, self.base_url, self.api_key, self.model = name, base_url.rstrip("/"), api_key, model
        self.input_rate, self.output_rate = input_rate, output_rate

    async def generate(self, prompt: str, instructions: str, max_output_tokens: int) -> ModelResult:
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    f"{self.base_url}/responses",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={"model": self.model, "instructions": instructions, "input": prompt,
                          "max_output_tokens": max_output_tokens, "stream": False, "store": False},
                )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderUnavailable(self.name) from exc

        if data.get("status") not in (None, "completed"):
            raise ProviderUnavailable(self.name)
        answer = data.get("output_text")
        if not isinstance(answer, str):
            chunks = [
                part.get("text", "")
                for item in data.get("output", []) if item.get("type") == "message"
                for part in item.get("content", []) if part.get("type") == "output_text"
            ]
            answer = "".join(chunks)
        if not answer or not answer.strip():
            raise ProviderUnavailable(self.name)

        usage = data.get("usage") or {}
        input_tokens, output_tokens = usage.get("input_tokens"), usage.get("output_tokens")
        total_tokens = usage.get("total_tokens")
        cost = None
        if isinstance(input_tokens, int) and isinstance(output_tokens, int) and self.input_rate is not None and self.output_rate is not None:
            cost = (input_tokens * self.input_rate + output_tokens * self.output_rate) / 1_000_000
        return ModelResult(
            self.name, str(data.get("model") or self.model), answer.strip(),
            input_tokens if isinstance(input_tokens, int) else None,
            output_tokens if isinstance(output_tokens, int) else None,
            total_tokens if isinstance(total_tokens, int) else None,
            cost, data.get("id"),
        )


class ModelOrchestrator:
    def __init__(self, providers: list[ModelProvider]):
        self.providers = providers

    async def generate(self, prompt: str, instructions: str, max_output_tokens: int) -> tuple[ModelResult, bool]:
        failures = []
        for index, provider in enumerate(self.providers):
            started = time.perf_counter()
            try:
                result = await provider.generate(prompt, instructions, max_output_tokens)
                logger.info("model_request_completed", extra={
                    "event": "model_request_completed", "provider": result.provider, "model": result.model,
                    "input_tokens": result.input_tokens, "output_tokens": result.output_tokens,
                    "total_tokens": result.total_tokens, "estimated_cost_usd": result.estimated_cost_usd,
                    "latency_ms": round((time.perf_counter() - started) * 1000, 2), "fallback_used": index > 0,
                })
                return result, index > 0
            except ProviderUnavailable:
                failures.append(provider.name)
                logger.warning("model_provider_failed", extra={
                    "event": "model_provider_failed", "provider": provider.name, "model": provider.model,
                    "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                })
        raise ProviderUnavailable("All configured providers failed: " + ", ".join(failures))


def _rate(env_name: str) -> float | None:
    try:
        value = os.getenv(env_name)
        return max(0.0, float(value)) if value else None
    except ValueError:
        return None


def build_orchestrator_from_env() -> ModelOrchestrator:
    configs: dict[str, dict[str, Any]] = {
        "openai": {"key": os.getenv("OPENAI_API_KEY"), "model": os.getenv("ORIOM7_OPENAI_MODEL"),
                   "url": os.getenv("ORIOM7_OPENAI_BASE_URL", "https://api.openai.com/v1"),
                   "in": _rate("ORIOM7_OPENAI_INPUT_USD_PER_MILLION"), "out": _rate("ORIOM7_OPENAI_OUTPUT_USD_PER_MILLION")},
        "deepseek": {"key": os.getenv("DEEPSEEK_API_KEY"), "model": os.getenv("ORIOM7_DEEPSEEK_MODEL"),
                     "url": os.getenv("ORIOM7_DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                     "in": _rate("ORIOM7_DEEPSEEK_INPUT_USD_PER_MILLION"), "out": _rate("ORIOM7_DEEPSEEK_OUTPUT_USD_PER_MILLION")},
    }
    preferred = [os.getenv("ORIOM7_MODEL_PRIMARY", "openai").lower(),
                 os.getenv("ORIOM7_MODEL_FALLBACK", "deepseek").lower(), "openai", "deepseek"]
    providers = []
    for name in dict.fromkeys(preferred):
        cfg = configs.get(name)
        if cfg and cfg["key"] and cfg["model"]:
            providers.append(ResponsesAPIProvider(name, cfg["url"], cfg["key"], cfg["model"], cfg["in"], cfg["out"]))
    return ModelOrchestrator(providers)
