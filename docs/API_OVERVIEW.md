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


## Hybrid search and grounded assistant

`POST /search` queries the permission-aware PostgreSQL first-party index and can optionally query the configured SerpApi Google adapter. Results expose canonical URLs, snippets, source provenance and retrieval timestamps. A requested provider that is not configured is listed in `unavailable_sources`; the API returns a partial status rather than claiming full federation.

`POST /assistant/responses` now accepts a `grounding` object with `search` and `minimum_sources`. When enabled, the API retrieves evidence before model invocation, supplies numbered source labels, and maps labels in the model output back to retrieved records. Unknown source labels are reported as invalid references. This is reference validation, not semantic proof that a source supports a claim.

See [Hybrid Search and Grounding](HYBRID_SEARCH_AND_GROUNDING.md) for database setup, external provider configuration, API examples and remaining limitations.


## Multilingual semantic retrieval

`POST /search` can combine the first-party PostgreSQL lexical index with an optional pgvector semantic index. When enabled, query and document embeddings are generated through the configured embeddings provider, and lexical/vector result lists are fused using reciprocal-rank fusion. Semantic matching is cross-language by default; strict language filtering is opt-in. Semantic retrieval requires pgvector migration 005 and backend embedding credentials. See [Hybrid Search and Grounding](HYBRID_SEARCH_AND_GROUNDING.md) for configuration, privacy, backfill and limitations. Similarity scores are relevance signals, not evidence of factual entailment.


## Evidence-linked knowledge graph

- `POST /knowledge/observations` — submit entities and provenance-bearing relationship candidates against an eligible indexed document. Candidates begin as `unverified`.
- `POST /knowledge/assertions/{assertion_id}/review` — token-protected review action; only an authenticated reviewer can accept or reject a candidate. Configure `ORIOM7_GRAPH_REVIEW_TOKEN` in backend secrets.
- `GET /knowledge/entities?q=...` — find canonical entities and aliases.
- `GET /knowledge/entities/{entity_id}` — read the entity's one-hop neighbourhood, returning accepted assertions only.

Apply migration `006_knowledge_graph.sql` after migrations 001–005. Assertions retain evidence document IDs, excerpts, confidence and reviewer audit data. Review is a human approval gate, not automatic fact verification. See [Knowledge Graph Foundation](KNOWLEDGE_GRAPH_FOUNDATION.md) for schema, examples and limitations.

- `POST /knowledge/documents/{document_id}/extract` — request model-assisted entity and relation extraction from one eligible indexed document. Candidate excerpts must match source text verbatim and all assertions remain unverified pending human review. Requires a configured model provider. Optional crawler-worker invocation is controlled by `ORIOM7_KNOWLEDGE_EXTRACTION_ENABLED` (default false).
