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
- `services/api/` — FastAPI service scaffold.
- `infra/` — deployment guidance.
- `data/` — data and indexing design.
- `research/hardware/` — exploratory hardware research.

## Product specifications
- [Software Architecture](docs/SOFTWARE_ARCHITECTURE_DOCUMENT.md)
- [Universal Language and Voice Access](docs/UNIVERSAL_LANGUAGE_AND_VOICE_ACCESS.md)
- [Universal Accessibility and Inclusion](docs/UNIVERSAL_ACCESSIBILITY_AND_INCLUSION.md)
- [Adaptive Accessibility System](docs/ADAPTIVE_ACCESSIBILITY_SYSTEM.md)
- [Adaptive Accessibility Engine — Technical Design](docs/ADAPTIVE_ACCESSIBILITY_ENGINE.md)
- [Adaptive Accessibility Engine package](packages/accessibility-engine/README.md)
- [Technical Specifications](docs/TECHNICAL_SPECIFICATIONS.md)
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md)
- [Architecture Decisions](docs/architecture/ADRS.md)
- [OpenAPI contract](contracts/openapi.json)

## Status and scope
This repository establishes the architecture baseline; it does not claim that a global search index, agent catalogue, proprietary models, cloud or silicon already exist. Targets such as 195+ countries/languages, 120+ agents and 300+ tools are ambitions, not current capabilities. Language support must be evaluated per language, dialect and task before it is advertised. Accessibility must be tested with assistive technologies and disabled users; automated scans alone are insufficient.

The Adaptive Accessibility Engine now includes a TypeScript profile resolver, JSON Schema, FastAPI profile endpoints, a PostgreSQL migration, a first Next.js settings screen and CI test workflows. Production OIDC/session middleware, database provisioning, application-wide preference application, speech/voice adapters and assistive-technology validation remain integration work.

ORIOM7 does not diagnose or treat medical or mental health conditions. Accessibility settings are user-selected accommodations, not diagnostic labels or inferred health profiles.

Security: never commit credentials, secrets or private customer data. See SECURITY.md.
