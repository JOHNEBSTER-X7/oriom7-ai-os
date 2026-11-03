# ORIOM7 — AI Search Engine & AI Operating System

ORIOM7 is a hybrid AI search and intelligence platform combining an independently operated search index with external search providers, plus multi-model orchestration for sourced answers, research workflows and developer APIs.

## Approved architecture decisions
1. Hybrid search: independent index plus external search providers.
2. Hybrid multi-model architecture: hosted model providers and a future self-hosted capability behind provider adapters.
3. Initial deployment: Vercel web frontend plus managed backend infrastructure.
4. Initial product priority: Search, AI assistant and developer API together.
5. Long-term ambition: proprietary AI cloud and hardware, developed progressively.

## Repository map
- `docs/` — architecture, specifications, implementation plan and ADRs.
- `contracts/` — machine-readable API contract.
- `apps/web/` — frontend implementation notes.
- `services/api/` — FastAPI service scaffold.
- `infra/` — deployment guidance.
- `data/` — data and indexing design.
- `research/hardware/` — exploratory hardware research.

## Status and scope
This repository establishes the architecture baseline; it does not claim that a global search index, agent catalogue, proprietary models, cloud or silicon already exist. Targets such as 195+ countries/languages, 120+ agents and 300+ tools are ambitions, not current capabilities.

Start with [the Software Architecture Document](docs/SOFTWARE_ARCHITECTURE_DOCUMENT.md), then review the [Technical Specifications](docs/TECHNICAL_SPECIFICATIONS.md), [Implementation Plan](docs/IMPLEMENTATION_PLAN.md), [ADRs](docs/architecture/ADRS.md) and [OpenAPI contract](contracts/openapi.json).

Security: never commit credentials, secrets or private customer data. See SECURITY.md.
