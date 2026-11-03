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


## Knowledge graph foundation

The API now includes a provenance-aware graph schema and endpoints for candidate entity/relation submission, token-protected human review, entity/alias lookup and accepted one-hop relationship reads. Candidate assertions remain hidden from graph reads until reviewed and accepted against eligible indexed evidence. This is a foundation, not yet an automated knowledge graph extraction or reasoning system. See [Knowledge Graph Foundation](docs/KNOWLEDGE_GRAPH_FOUNDATION.md).
