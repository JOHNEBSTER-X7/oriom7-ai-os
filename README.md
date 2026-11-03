# ORIOM7 — AI Search Engine & AI Operating System

ORIOM7 is a hybrid AI search and intelligence platform combining an independently operated search index with external search providers, plus multi-model orchestration for sourced answers, research workflows and developer APIs.

A foundational product commitment is universal access: people must be able to use ORIOM7 through voice, translation, spoken answers and simple visual interactions even when they cannot read or write or do not speak the source language.

## Approved architecture decisions
1. Hybrid search: independent index plus external search providers.
2. Hybrid multi-model architecture: hosted model providers and a future self-hosted capability behind provider adapters.
3. Initial deployment: Vercel web frontend plus managed backend infrastructure.
4. Initial product priority: Search, AI assistant and developer API together.
5. Long-term ambition: proprietary AI cloud and hardware, developed progressively.
6. Universal language and low-literacy access is a core product requirement, not a late add-on.

## Repository map
- `docs/` — architecture, specifications, implementation plan, universal language/voice access and ADRs.
- `contracts/` — machine-readable API contract.
- `apps/web/` — frontend implementation notes.
- `services/api/` — FastAPI service scaffold.
- `infra/` — deployment guidance.
- `data/` — data and indexing design.
- `research/hardware/` — exploratory hardware research.

## Status and scope
This repository establishes the architecture baseline; it does not claim that a global search index, agent catalogue, proprietary models, cloud or silicon already exist. Targets such as 195+ countries/languages, 120+ agents and 300+ tools are ambitions, not current capabilities. Language support must be evaluated per language, dialect and task before it is advertised.

Start with [the Software Architecture Document](docs/SOFTWARE_ARCHITECTURE_DOCUMENT.md), [Universal Language and Voice Access](docs/UNIVERSAL_LANGUAGE_AND_VOICE_ACCESS.md), [Technical Specifications](docs/TECHNICAL_SPECIFICATIONS.md), [Implementation Plan](docs/IMPLEMENTATION_PLAN.md), [ADRs](docs/architecture/ADRS.md) and [OpenAPI contract](contracts/openapi.json).

Security: never commit credentials, secrets or private customer data. See SECURITY.md.
