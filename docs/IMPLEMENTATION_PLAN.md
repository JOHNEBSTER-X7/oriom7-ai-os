# ORIOM7 Implementation Plan

## Delivery principle

Build one complete user-facing vertical slice before expanding subsystem count. Search, assistant and developer API are first-release priorities, delivered through shared infrastructure and a small number of deployable units.

## Phase 0 — readiness (indicative 1–2 weeks)

Deliverables:
- Confirm legal/source acquisition policy and threat model.
- Select managed PostgreSQL, Redis, queue, object storage and search infrastructure.
- Select first external search provider and first model providers.
- Define representative search and assistant evaluation set.
- Establish dev/staging/prod environments, CI and secret management.

Exit criteria: architecture decisions recorded; provider/data boundaries agreed; security baseline and deployment pipeline operational.

## Phase 1 — integrated MVP (indicative 4–8 weeks)

Deliverables:
- Next.js application with search and assistant experiences.
- FastAPI API with status, search, assistant, models and usage endpoints.
- Developer authentication, tenant scoping, quotas and request IDs.
- One external search adapter and a minimal first-party curated index.
- At least two model-provider adapters where access and evaluation permit.
- Evidence-linked answers and source presentation.
- Background worker and queue for ingestion.
- Automated tests and basic observability.

Exit criteria: search returns normalised first-party and external results; assistant uses retrieved evidence and exposes references; developer API contract is tested; failure and degraded-mode behaviour is demonstrated.

## Phase 2 — search quality (indicative 4–8 weeks)

Expand approved source ingestion; improve parsing, canonicalisation, deduplication and freshness; evaluate lexical, semantic and hybrid ranking; add reranking only when tests show improvement; build source quality and abuse controls; track recall, precision, freshness and index coverage.

## Phase 3 — developer platform (indicative 3–6 weeks)

API key lifecycle, usage dashboard and quota management; SDK and quick starts; versioning and change policy; billing integration only after pricing and unit economics are validated; developer support and operations documentation.

## Phase 4 — multilingual and regional expansion

Language detection and query translation where useful; locale-aware search and source selection; multilingual evaluation and human review; regional privacy and data-residency controls; rollout based on quality evidence.

## Phase 5 — agents and scale

Agent registry and explicit capability/permission model; tool catalogue with allowlists and scoped credentials; sandboxed execution and human approval for consequential actions; queue-based orchestration and budgets. Decompose services only where independent scaling or ownership requires it.

## Phase 6 — proprietary AI cloud and hardware research

Measure workloads and inference bottlenecks; benchmark open/self-hosted models against hosted APIs; model GPU/accelerator costs, utilisation and power requirements; prototype inference infrastructure before training infrastructure. Hardware progresses through simulation and FPGA prototypes before any test-chip or ASIC commitment. Keep separate investment gates and no production dependency until reliability and economics are proven.

## Core delivery risks

| Risk | Mitigation |
|---|---|
| Scope expansion | Phase gates and measurable exit criteria |
| Search data rights | Source-level approval and auditable acquisition policy |
| Model spend | Per-tenant quotas, routing and usage telemetry |
| Hallucinated citations | Citation-to-evidence validation and evaluation |
| Provider outages | Timeouts, retries, circuit breakers and fallback |
| Operational overload | Managed infrastructure and modular architecture |
