# ORIOM7 — AI Search Engine & AI Operating System

ORIOM7 is a hybrid AI search and intelligence platform combining an independently operated search index with external search providers, plus multi-model orchestration for sourced answers, research workflows and developer APIs.

## Four universal product pillars

1. Universal Search — discover information across sources and languages.
2. Universal Intelligence — understand, explain and help solve problems using evidence.
3. Universal Access — voice, translation, spoken answers and low-literacy interaction.
4. Universal Accessibility and Inclusion — adaptive access for people with diverse access needs.

## Approved architecture

- Hybrid search: independent index plus external search providers.
- Hybrid multi-model architecture behind provider adapters.
- Vercel web frontend plus managed backend infrastructure.
- Search, AI assistant and developer API as the initial product priorities.
- Universal language, low-literacy access and adaptive accessibility are core requirements.

## Repository map

- docs/ — architecture, specifications and implementation plans.
- packages/accessibility-engine/ — shared accessibility preference resolver.
- contracts/ — machine-readable API contract.
- apps/web/ — Next.js frontend and research workspace.
- services/api/ — FastAPI service, retrieval, embeddings and orchestration.
- services/api/migrations/ — ordered PostgreSQL schema migrations.
- research/ — exploratory research.

## Search and intelligence capabilities

The backend includes PostgreSQL lexical retrieval, optional pgvector semantic retrieval, external search adapters, reciprocal-rank fusion, controlled source ingestion, evidence-grounded assistant prompting, an evidence-linked knowledge graph, research workspaces and autonomous research jobs.

Semantic retrieval supports configurable embedding dimensions. The default remains 1,536 dimensions. Migration 011 introduces dimension-aware vector storage and allows multiple embedding models per document. HNSW cosine indexing is used up to 2,000 dimensions; higher dimensions use exact cosine ranking. See [Vector Retrieval and Embeddings](docs/VECTOR_RETRIEVAL_AND_EMBEDDINGS.md).

## Status and limitations

The repository establishes the architecture and implemented foundations; it does not claim that a complete global search index, proprietary foundation models, cloud or hardware already exist. Broad language and vertical coverage must be demonstrated through licensed data acquisition and measurable evaluation. Search and embedding outputs must retain source provenance; semantic similarity is not proof of factual correctness.

Never commit credentials, secrets or private customer data. See SECURITY.md.
