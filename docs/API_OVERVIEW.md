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

- `POST /knowledge/observations` — submit entities and evidence-linked relationship candidates; candidates begin unverified.
- `POST /knowledge/assertions/{assertion_id}/review` — protected human review action.
- `GET /knowledge/entities?q=...` and `GET /knowledge/entities/{entity_id}` — entity lookup and accepted one-hop relationships.
- `GET /knowledge/entities/{entity_id}/resolution-candidates` — similarity-ranked possible duplicate identities; suggestions do not merge records.
- `GET /knowledge/assertions/potential-conflicts?predicate=...&single_valued=true` — find overlapping accepted claims with different objects for a caller-designated single-valued predicate. Results are potential inconsistencies for human assessment.
- `GET /knowledge/entities/{entity_id}/paths?max_depth=2&as_of=YYYY-MM-DD` — bounded multi-hop paths through accepted, currently eligible evidence; each edge retains provenance.
- `POST /knowledge/documents/{document_id}/extract` — model-assisted candidate extraction. Verbatim excerpt validation is required and all output remains unverified.

Apply migrations 006–008 after 001–005. Migration 008 adds optional `valid_from` and `valid_to` dates. Temporal dates are recorded only when supported by source material; null means unknown. Multi-hop traversal is limited to three edges. Neither entity resolution nor conflict triage performs automatic merging, fact acceptance or contradiction resolution. See [Knowledge Graph Foundation](KNOWLEDGE_GRAPH_FOUNDATION.md).


## Graph-aware research assistant

`POST /assistant/responses` now supplements hybrid search with bounded knowledge-graph context when the API has a database-backed graph. The service matches explicit names/aliases in the question, then retrieves only accepted assertions whose source documents remain indexed, non-deleted, rights-cleared and robots-eligible. It does not treat unverified graph candidates as facts.

Search citations use `[S#]`; graph citations use a separate `[G#]` namespace. Both are mapped to retrieved source records. The response adds `grounding.knowledge_graph` with matched entities, assertion count, source citations and potential inconsistencies. Potential inconsistencies are unresolved review signals, not proven contradictions. Connected relationships do not establish causation or transitive truth. See [Graph-Aware Research Assistant](GRAPH_AWARE_RESEARCH_ASSISTANT.md).


## Research intelligence workspace

The web application provides a `/research` workspace that orchestrates the existing search, assistant and knowledge graph APIs. The entity detail response now includes source title, canonical URL and publication/retrieval timestamps alongside the evidence excerpt and temporal validity. The interface displays direct accepted relationships, bounded path summaries, a dated timeline and source comparison. See [Research Intelligence Workspace](RESEARCH_INTELLIGENCE_WORKSPACE.md).


## Evidence verification centre

- `GET /v1/knowledge/assertions/review-queue`: paginated unverified assertions with source provenance; reviewer allow-list required.
- `POST /v1/knowledge/assertions/{assertion_id}/review`: accept/reject decision; authenticated reviewer allow-list and review token required.

The Next.js interface is available at `/research/review`; its same-origin proxy keeps the review token server-side. See [Evidence Verification Centre](EVIDENCE_VERIFICATION_CENTRE.md).
