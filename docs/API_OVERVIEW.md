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
