# ORIOM7 API Overview

Base path: `/v1`

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/status` | Liveness/status information |
| GET | `/models` | Models enabled for caller |
| POST | `/search` | Hybrid search |
| POST | `/assistant/responses` | Evidence-aware assistant response |
| GET | `/usage` | Caller usage summary |
| POST | `/assistant/presentation` | Resolve accessibility-aware response-formatting directives for the assistant |

All endpoints require an authenticated context except a deliberately configured public health endpoint. Enforce tenant, scope, quota and request-size policies server-side. Detailed contract: `../contracts/openapi.json`.


## Assistant presentation adapter

`POST /assistant/presentation` requires an authenticated subject. It reads the caller's saved accessibility profile and returns structured, model-provider-neutral presentation directives: preferred language, plain-language preference, answer detail, short-answer-first, step-by-step structure, reduced content density and speech-output preferences.

The endpoint accepts optional temporary profile overrides. These are validated against the same profile contract and are not persisted. The adapter explicitly preserves citations, uncertainty and safety warnings.

This endpoint does not generate an AI answer, translate content, call a model provider or synthesize speech. The assistant orchestration layer must consume these directives and connect the corresponding capabilities before those features can be advertised as operational.

## Model orchestration

- `GET /models` — authenticated catalogue of configured providers and their enabled capabilities.
- `POST /assistant/responses` — authenticated model generation using the user's saved accessibility preferences.

The initial provider adapters use the Responses API contract. Configure provider credentials and explicit model IDs in the deployment secret manager; see [Model Provider Configuration](MODEL_PROVIDER_CONFIGURATION.md). The primary provider is attempted before the configured fallback. Token usage and provider latency are logged without logging prompts; cost estimates are emitted only when token prices are configured.

The first generation slice is non-streaming and text-only. Retrieval grounding, source validation, tool execution, streaming and durable conversation history are not yet connected. Responses explicitly report `grounding.status = not_connected`; the model is instructed not to invent citations.
