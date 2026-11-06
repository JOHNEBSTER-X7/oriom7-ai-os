# ORIOM7 — AI Search Engine & AI Operating System

ORIOM7 is a hybrid AI search and intelligence platform combining an independently operated search index with external search providers, plus multi-model orchestration for sourced answers, research workflows and developer APIs.

Its product promise is universal access: people should be able to use ORIOM7 regardless of language, literacy, sight, hearing, mobility, cognitive needs or digital confidence.

## Four universal product pillars
1. **Universal Search** — discover information across sources and languages.
2. **Universal Intelligence** — understand, explain and help solve problems using evidence.
3. **Universal Access** — voice, translation, spoken answers and low-literacy interaction.
4. **Universal Accessibility and Inclusion** — adaptive access for blind and low-vision users and people with neurological, motor, cognitive, learning, sensory or mental-health-related access needs.

## Approved architecture decisions
1. Hybrid search: independent index plus external search providers.
2. Hybrid multi-model architecture: hosted model providers and a future self-hosted capability behind provider adapters.
3. Initial deployment: Vercel web frontend plus managed backend infrastructure.
4. Initial product priority: Search, AI assistant and developer API together.
5. Long-term ambition: proprietary AI cloud and hardware, developed progressively.
6. Universal language, low-literacy access and adaptive accessibility are core requirements, not late add-ons.

## Repository map
- `docs/` — architecture, specifications, implementation plan, universal language/voice access, accessibility/inclusion and adaptive accessibility.
- `docs/COMMERCIAL_DEVELOPER_API_PLATFORM_V1.md` — commercial developer API foundation, readiness status and production launch gates.
- `packages/accessibility-engine/` — typed preference model, JSON Schema, resolver and contract test cases.
- `contracts/` — machine-readable API contract.
- `apps/web/` — frontend implementation notes.
- `services/api/` — FastAPI service, accessibility endpoints and provider-independent model orchestration.
- `infra/` — deployment guidance.
- `data/` — data and indexing design.
- `research/hardware/` — exploratory hardware research.
- `services/api/knowledge_graph.py` — evidence-linked entity and relationship API.

## Product specifications
- [Software Architecture](docs/SOFTWARE_ARCHITECTURE_DOCUMENT.md)
- [Universal Language and Voice Access](docs/UNIVERSAL_LANGUAGE_AND_VOICE_ACCESS.md)
- [Universal Accessibility and Inclusion](docs/UNIVERSAL_ACCESSIBILITY_AND_INCLUSION.md)
- [Adaptive Accessibility System](docs/ADAPTIVE_ACCESSIBILITY_SYSTEM.md)
- [Adaptive Accessibility Design System](docs/ACCESSIBILITY_DESIGN_SYSTEM.md)
- [Adaptive Accessibility Engine — Technical Design](docs/ADAPTIVE_ACCESSIBILITY_ENGINE.md)
- [Adaptive Accessibility Engine package](packages/accessibility-engine/README.md)
- [Technical Specifications](docs/TECHNICAL_SPECIFICATIONS.md)
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md)
- [Architecture Decisions](docs/architecture/ADRS.md)
- [OpenAPI contract](contracts/openapi.json)

## Status and scope
This repository establishes the architecture baseline; it does not claim that a global search index, agent catalogue, proprietary models, cloud or silicon already exist. Targets such as 195+ countries/languages, 120+ agents and 300+ tools are ambitions, not current capabilities. Language support must be evaluated per language, dialect and task before it is advertised. Accessibility must be tested with assistive technologies and disabled users; automated scans alone are insufficient.

The Adaptive Accessibility Engine now includes a shared TypeScript profile resolver, a global Next.js accessibility provider, local-only preference storage, account-sync endpoints, PostgreSQL migration and CI workflows. The provider applies text scaling, typography, themes, contrast, target sizing and reduced-motion preferences across the web application. A FastAPI assistant presentation endpoint resolves saved or temporary preferences into structured output directives while preserving citations, uncertainty and safety warnings. Production identity integration, database provisioning, actual model orchestration, translation, speech/voice adapters and assistive-technology validation remain integration work.

ORIOM7 does not diagnose or treat medical or mental health conditions. Accessibility settings are user-selected accommodations, not diagnostic labels or inferred health profiles.

Security: never commit credentials, secrets or private customer data. See SECURITY.md.


## Hybrid search implementation

The API now includes PostgreSQL lexical retrieval over a rights-basis-filtered first-party index, an optional SerpApi Google search adapter, canonical URL deduplication and evidence-aware assistant prompting with source-label mapping. The index schema is in `services/api/migrations/002_search_index.sql`. Controlled source registration, single-page ingestion and a PostgreSQL-backed distributed crawl queue/worker are implemented. Optional pgvector semantic retrieval is now available behind explicit configuration; multilingual evaluation, passage-level retrieval and semantic claim-to-source verification remain outstanding. See [Hybrid Search and Grounding](docs/HYBRID_SEARCH_AND_GROUNDING.md).


The search API now supports optional pgvector semantic retrieval alongside PostgreSQL lexical search, with reciprocal-rank fusion and cross-language vector matching when configured. Semantic indexing requires migration 005 and an explicitly configured embedding provider; see [Hybrid Search and Grounding](docs/HYBRID_SEARCH_AND_GROUNDING.md). Do not advertise broad language coverage until per-language retrieval quality has been benchmarked.


## Knowledge graph and intelligence layer

The graph now supports evidence-linked candidate extraction, temporal relationship validity, similarity-ranked entity resolution suggestions, potential-conflict triage for explicitly single-valued predicates, and bounded multi-hop paths through accepted assertions. Every traversed relationship retains its source evidence. Entity suggestions never auto-merge records; conflict reports are hypotheses for human review, not proof of contradiction. Apply migrations 006–008 after 001–005. See [Knowledge Graph Foundation](docs/KNOWLEDGE_GRAPH_FOUNDATION.md).


## Graph-aware research assistant

The assistant can now use accepted, source-backed knowledge-graph assertions alongside hybrid search. It keeps graph citations separate from search citations and reports unresolved potential inconsistencies without presenting them as verified contradictions. This is a bounded first integration: entity matching is name/alias based, paths do not prove causation, and semantic claim verification remains future work. See [Graph-Aware Research Assistant](docs/GRAPH_AWARE_RESEARCH_ASSISTANT.md).


## Research intelligence workspace

The Next.js app now includes a dedicated `/research` workspace for hybrid source search, graph entity exploration, source comparison, historical relationship timelines and Markdown research-report export. It uses a same-origin authenticated API proxy and keeps graph evidence provenance visible. See [Research Intelligence Workspace](docs/RESEARCH_INTELLIGENCE_WORKSPACE.md).


## Evidence verification centre

The `/research/review` workspace lets explicitly authorised human reviewers inspect pending graph assertions, open their source, and accept or reject claims. The API restricts access to an explicit authenticated-subject allow-list and a server-held review token. See [Evidence Verification Centre](docs/EVIDENCE_VERIFICATION_CENTRE.md).


## Autonomous research agents

ORIOM7 now queues user-initiated research for a separate PostgreSQL-backed worker. It uses specialist planning, evidence-retrieval and synthesis stages, stores run history, retries bounded failures and supports opt-in recurring schedules. Candidate graph assertions still require human review. Apply migration 010 and run `python worker.py` alongside the API. See [Autonomous Research Agents](docs/AUTONOMOUS_RESEARCH_AGENTS.md).

## Multidimensional vector retrieval

ORIOM7's existing pgvector semantic-search path now supports configurable embedding dimensions and multiple embedding models per document. The default remains 1,536 dimensions. HNSW indexing is used up to 2,000 dimensions; higher dimensions use exact cosine ranking. See [Vector Retrieval and Embeddings](docs/VECTOR_RETRIEVAL_AND_EMBEDDINGS.md).

## Commercial developer API foundation

The commercial developer API now includes hashed developer API keys, OIDC-backed account identity, Stripe checkout/webhook foundations, subscription-derived monthly quotas, usage metering, a preview text-embedding endpoint, a provider-backed translation endpoint and a provider-backed OCR/document extraction endpoint. Translation and OCR remain planned until operators configure and evaluate their HTTPS providers. OCR accepts PDF, PNG, JPEG and TIFF files up to 15 MB, validates file signatures, forwards uploads to the configured provider, does not persist originals and meters successful extraction by pages. Speech, text-to-speech, durable document storage, malware scanning and structured table/field extraction remain future work. Live billing and public production readiness are not implied. See [Commercial Developer API Platform V1](docs/COMMERCIAL_DEVELOPER_API_PLATFORM_V1.md).


## Identity and commercial billing foundation

The account workspace now includes authenticated account profiles, organisation creation and owner membership, a plan catalogue, subscription/invoice read models and a monthly usage-ledger endpoint. Migration 013 adds the underlying account, organisation, subscription, invoice, payment-event and usage tables. All private routes reuse the existing trusted `authenticated_subject` dependency. No password-based login or payment provider is activated; checkout is disabled, paid pricing is pending, and usage-ledger metering/quota enforcement remains integration work. See [Identity and Commercial Billing Engine V1](docs/IDENTITY_AND_COMMERCIAL_BILLING_ENGINE_V1.md).


## OIDC identity, organisation management and Stripe billing

The identity and commercial milestone now includes a generic managed OIDC authorization-code + PKCE web sign-in flow, RS256/JWKS access-token verification in the API, secure HttpOnly access-token cookies, organisation invitations and role management, Stripe Checkout Sessions, timestamp-verified/idempotent Stripe webhooks, subscription/invoice synchronization, and subscription-derived monthly API request quotas.

Apply database migrations 001–015. Configure OIDC issuer, API audience, JWKS endpoint and confidential web-client settings before enabling sign-in. Configure Stripe test-mode secret/webhook keys, Builder/Business Price IDs and trusted HTTPS return URLs before checkout becomes available. No credentials are included and live billing is not enabled by this repository alone.

Organisation invitation tokens are hashed and expire after seven days, but automated email delivery is not configured; the token must currently be delivered securely out-of-band. Email verification and account recovery are handled by the selected OIDC provider. See [Identity, Organisation and Commercial Billing V1](docs/IDENTITY_AND_COMMERCIAL_BILLING_ENGINE_V1.md) for exact environment variables, migration order, integration boundaries and production launch gates.


## Speech Intelligence V1

The API now contains provider-backed speech-to-text and text-to-speech adapters. Transcription accepts bounded audio uploads, validates basic media signatures, returns provider transcript metadata and optional timestamped segments/speaker labels, and meters audio seconds. Synthesis accepts bounded text and returns provider-generated audio bytes while metering input characters. Both providers are operator-configured through trusted HTTPS endpoints; no provider credentials are exposed to clients. Speech products remain planned until configured, tested and evaluated. There is no proprietary speech engine, built-in diarisation, streaming synthesis or durable audio storage yet. See [Commercial Developer API Platform V1](docs/COMMERCIAL_DEVELOPER_API_PLATFORM_V1.md).


### Real-Time Voice Intelligence V1

An authenticated `POST /v1/assistant/voice-turn` pipeline connects speech transcription, the existing assistant orchestrator and accessibility profile, and text-to-speech. Clients may pass up to 12 previous user/assistant messages for request-scoped conversational context. Synthesized audio is returned in the response body; transcript and answer are returned in bounded base64 response headers. This is sequential request/response processing, not duplex streaming, and conversation history is not durably stored. See [Commercial Developer API Platform V1](docs/COMMERCIAL_DEVELOPER_API_PLATFORM_V1.md).
