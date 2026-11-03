# ORIOM7 Software Architecture Document

**Version:** 1.0  
**Date:** 3 November 2026  
**Status:** Approved baseline for implementation planning

## 1. Executive summary

ORIOM7 is a hybrid AI search engine and assistant with a developer API. It will operate an independent search index while federating to external search providers. A model orchestration layer selects among hosted and, later, self-hosted models according to task suitability, latency, quality, availability, privacy and cost.

The initial delivery uses a Vercel-hosted web experience and managed backend infrastructure. Search, assistant and developer API are co-equal priorities. The architecture remains modular so the platform can progressively add agents, multilingual capabilities, a proprietary AI cloud and hardware research without prematurely building a large distributed system.

## 2. Goals and non-goals

### Goals
- Deliver search with source attribution.
- Provide an assistant that synthesises retrieved information and explains its evidence.
- Expose stable, authenticated developer APIs.
- Combine a growing first-party index with external search providers.
- Support model substitution and policy-based routing.
- Establish privacy, security, observability, evaluation and cost controls.
- Preserve a path to multilingual expansion, agents, AI infrastructure and hardware R&D.

### Non-goals for the first release
- Crawl and index the entire public web.
- Train a frontier foundation model.
- Launch a global agent catalogue at the outset.
- Operate proprietary data centres or manufacture production silicon.
- Decompose every component into a separate microservice before scale requires it.

## 3. Product scope and user journeys

Initial product surfaces:
- **Search:** query input, ranked results, snippets, source links and filters.
- **Assistant:** conversational questions, evidence-backed responses and conversation history.
- **Developer API:** API keys, documentation, request/response schemas, rate limits and usage visibility.

Initial assistant modes may be exposed progressively: Chat, Research, Coding, Business and Education. Mode selection changes orchestration policy and response format; it does not imply a separate model for every mode.

## 4. Context and system boundaries

ORIOM7 interacts with end users through the web application; developers through versioned APIs; external search services through provider adapters; model vendors through model adapters; identity providers through OIDC; and managed database, cache, object storage and queue services.

The platform must respect provider terms, robots directives, copyright, privacy and applicable law. Index only content for which the acquisition method and intended use are permitted.

## 5. Logical architecture

### 5.1 Experience layer
Next.js and TypeScript web application. Vercel is the initial frontend hosting target. The client handles presentation and streaming UX; business policy remains server-side.

### 5.2 API and edge layer
A versioned API application provides authentication, request validation, rate limits, quotas, idempotency, request IDs and response streaming. Public endpoints use a stable contract independent of internal services.

### 5.3 Identity, tenant and policy layer
OIDC-based user authentication; API-key authentication for developers; tenant-aware authorisation; usage plans; model and search policy enforcement. Secrets are never sent to the browser.

### 5.4 Query and orchestration layer
A request orchestrator classifies intent, applies policy, creates a retrieval plan, selects search sources and models, and composes a grounded response. It records provider and model metadata for observability and evaluation.

### 5.5 Hybrid search subsystem
Two complementary retrieval paths:

1. **ORIOM7-owned index:** approved crawler/connectors → fetch queue → content extraction → canonicalisation → deduplication → metadata and access policy → lexical/vector indexing → ranking.
2. **External search providers:** adapters normalise provider results into one internal representation.

A retrieval planner selects owned index, external providers or both. A fusion/reranking stage deduplicates results, scores relevance and preserves canonical URLs, timestamps and source provenance. Search responses distinguish indexed results from externally retrieved results where useful.

### 5.6 Model subsystem
A model registry records capabilities, context limits, supported modalities, regional constraints, cost metadata and operational status. Provider adapters normalise invocation, streaming, tool calling, errors and token usage. A policy router chooses a model based on request type, policy, latency, cost and availability. A future self-hosted model runtime implements the same interface.

### 5.7 Knowledge and data layer
- PostgreSQL: users, tenants, API keys (hashed), usage, conversations, provider configuration, jobs and metadata.
- Search engine: lexical inverted index and filtering.
- Vector database: embeddings and semantic retrieval where evaluation demonstrates value.
- Object storage: raw/derived documents and large artifacts subject to retention rules.
- Redis: cache, ephemeral state, rate-limit counters and short-lived coordination.
- Optional graph store: only when knowledge-graph use cases justify the operational cost.

### 5.8 Background processing
Managed queues and worker processes handle crawling, parsing, embedding, indexing, scheduled refresh, evaluation and long-running research. These workloads must not run inside short-lived frontend request handlers.

## 6. Deployment topology

- Web frontend: Vercel.
- API: managed container/serverless platform appropriate for persistent connections and streaming.
- Workers: managed background workers with queue-based execution.
- Database/cache/search/vector/object storage: managed services initially.
- CI/CD: GitHub Actions; immutable build artifacts and environment separation.

Use separate development, staging and production environments. Long-running crawlers and indexing workers remain separate from the Vercel web runtime.

## 7. Core request flows

### Search
1. Client submits a query to the versioned search endpoint.
2. API authenticates, validates and applies quota.
3. Retrieval planner selects owned-index and external provider sources.
4. Adapters retrieve candidates concurrently with timeouts.
5. Normalisation, deduplication, ranking and optional reranking run.
6. API returns results with provenance, source type and timing metadata.

### Assistant
1. Client submits a question and optional conversation context.
2. Policy layer validates tenant, data permissions and usage.
3. Orchestrator creates a retrieval plan and collects evidence.
4. Model router selects an eligible model.
5. Model generates a response using retrieved evidence.
6. Response is checked for citation mapping and policy compliance.
7. Client receives streamed content and structured source references.

## 8. API surface

Initial versioned endpoints:
- `GET /v1/status`
- `GET /v1/models`
- `POST /v1/search`
- `POST /v1/assistant/responses`
- `GET /v1/usage`

The OpenAPI contract is in `../contracts/openapi.json`. Breaking changes require a new API version or a documented migration path.

## 9. Reliability, performance and quality

Initial service objectives are provisional engineering targets and must be validated with production traffic:
- API availability target: 99.5% monthly for the initial beta.
- Search API p95 target: under 3 seconds for a bounded initial source set.
- Time to first assistant token target: under 2.5 seconds where provider and retrieval performance permit.
- Every request has a correlation ID.
- Provider calls have explicit timeouts, bounded retries and circuit breaking.
- Degraded mode returns available results when one provider fails.
- Quality is measured with relevance, citation correctness, freshness, latency and cost evaluation sets.

Do not advertise these targets as achieved service levels until measured.

## 10. Security, privacy and governance

- TLS in transit and managed encryption at rest.
- OIDC sessions and hashed/rotatable developer API keys.
- Tenant-scoped data access enforced at API and data layers.
- Principle of least privilege and separate service identities.
- Secret manager for credentials.
- Rate limits, quotas, abuse detection and audit trails.
- Data minimisation, retention controls, export/deletion workflows and privacy notices.
- Respect source-site access rules, licences, terms, robots directives and applicable data protection law.
- Prompt injection and untrusted retrieved content are treated as data, never policy instructions.
- Tool execution uses allowlists, scoped credentials, sandboxing and explicit permissions.

## 11. Observability and evaluation

Collect structured metrics for request volume, p50/p95/p99 latency, errors, provider timeouts, token usage, cost, cache hit rates, index freshness, queue depth and retrieval quality. Trace a request across API, retrieval, model and worker boundaries. Redact secrets and sensitive user content.

Maintain offline evaluation sets for search relevance, freshness, citation precision/recall, answer groundedness, refusal behaviour, multilingual quality and cost. Require evaluation evidence before promoting ranking or model-routing changes.

## 12. Progressive roadmap

- **Phase 0:** product boundaries, threat model, provider selection, evaluation set and deployment foundations.
- **Phase 1:** integrated vertical slice for web, API, hybrid retrieval, assistant and developer authentication.
- **Phase 2:** owned-index ingestion, freshness and relevance improvements.
- **Phase 3:** developer platform, billing/usage, SDK and additional modes.
- **Phase 4:** multilingual and country-aware retrieval expansion.
- **Phase 5:** agent workflows and scale optimisation based on demonstrated demand.
- **Phase 6:** proprietary AI cloud and hardware research, gated by measurable workloads, financing and technical validation.

Indicative durations are planning estimates only: Phase 0 1–2 weeks; Phase 1 4–8 weeks; Phase 2 4–8 weeks; Phase 3 3–6 weeks. Delivery depends on team size, provider access, security review and evaluation results.

## 13. Risks and mitigations

- **Index coverage and freshness:** start with bounded, permitted sources; measure freshness and coverage.
- **External provider dependency:** adapters, multiple providers and graceful degradation.
- **Model cost and latency:** routing policy, quotas, caching and measured model selection.
- **Hallucinations or false citations:** evidence-linked generation and citation validation.
- **Prompt injection:** isolate retrieved text from system policy and restrict tool privileges.
- **Premature complexity:** modular application and managed services until scale justifies decomposition.
- **Hardware ambition:** keep R&D separate from production roadmap and validate workloads before investment.

## 14. Acceptance criteria for architecture baseline

- Search, assistant and developer API share consistent identity, policy and usage controls.
- Search can combine first-party index and external providers.
- Model providers can be swapped without changing public API contracts.
- Responses preserve source provenance.
- Background ingestion is queue/worker based.
- Environments, secrets, logs and tenant access are separated.
- API schemas and core architecture decisions are version-controlled.
