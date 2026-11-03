# Architecture Decision Records

## ADR-001 — Hybrid search
**Status:** Accepted. Combine an independently operated search index with external search providers. This balances long-term differentiation and control with early coverage. Build ingestion/index/ranking and provider adapters; respect source rights and terms.

## ADR-002 — Hybrid multi-model
**Status:** Accepted. Support multiple hosted model providers and a consistent interface for future self-hosted models. Route by task quality, latency, cost, capability and policy.

## ADR-003 — Vercel plus managed backend
**Status:** Accepted. Vercel hosts the initial web frontend; managed backend services host API, data, search and workers. Keep long-running jobs outside the frontend runtime.

## ADR-004 — Three integrated MVP priorities
**Status:** Accepted. Search, AI assistant and developer API are co-equal initial priorities, sharing identity, usage, retrieval and provenance.

## ADR-005 — Progressive proprietary cloud and hardware
**Status:** Accepted. Pursue proprietary AI cloud and hardware progressively, not as launch dependencies. Gate investment on measured workloads, reliability, financing and technical validation.
