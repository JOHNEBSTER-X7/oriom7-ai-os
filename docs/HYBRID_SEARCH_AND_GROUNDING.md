# ORIOM7 Hybrid Search and Evidence Grounding

## What is implemented

The API now has a provider-neutral retrieval contract and two retrieval paths:

1. **ORIOM7-owned index:** PostgreSQL full-text search over the `search_documents` table, using a weighted generated `tsvector`, GIN index, query ranking and highlighted excerpts.
2. **External web search:** an optional SerpApi Google organic-results adapter. It normalises result title, canonical URL, snippet, provider, retrieval time and source type into the same internal result model.

The retrieval service applies reciprocal-rank fusion across provider-ranked lists so incomparable provider score scales are not mixed directly, then deduplicates canonical URLs while retaining the strongest fused rank. External results are transient; this adapter does not crawl or persist third-party page content.

## Database setup

Apply migrations in order:

```bash
psql "$DATABASE_URL" -f services/api/migrations/001_accessibility_profiles.sql
psql "$DATABASE_URL" -f services/api/migrations/002_search_index.sql
psql "$DATABASE_URL" -f services/api/migrations/003_search_ingestion.sql
psql "$DATABASE_URL" -f services/api/migrations/004_distributed_crawl_queue.sql
psql "$DATABASE_URL" -f services/api/migrations/005_semantic_search.sql
```

The index searches only records where:
- `index_status = 'indexed'`
- `rights_basis` is non-empty
- `robots_status` is `allowed` or `not_applicable`
- `deleted_at IS NULL`

This is a query-time eligibility filter, not a substitute for a documented source approval process. A source must be reviewed for terms, rights, privacy, retention and deletion obligations before indexing.

The API includes a controlled single-page ingestion endpoint and operator-managed source registry. Source registration requires a documented rights basis, approval reference and operator identity. This is an operator attestation, not an independent legal approval system; the organisation must verify source terms, licences, privacy, retention and deletion rights before registration.

## External search configuration

Set `SERPAPI_API_KEY` in the backend secret manager. Optional `ORIOM7_SEARCH_COUNTRY` defaults to `gb`. Never put the secret in the web client or commit it to Git.

The adapter calls `https://serpapi.com/search.json` with `engine=google`, query, result count and country/language preferences. It consumes the `organic_results` fields `title`, `link` and `snippet`. It rejects non-HTTP(S) links and does not store the API key in application logs.

SerpApi reference: https://serpapi.com/search-api

## API usage

### Search

`POST /v1/search`

```json
{
  "query": "grid-scale battery storage",
  "sources": ["oriom7_index", "external"],
  "limit": 10,
  "language": "en-GB"
}
```

If a requested source is not configured, the response reports `status: partial` and lists `unavailable_sources`. It does not claim that an unavailable source was searched.

### Grounded assistant

`POST /v1/assistant/responses`

```json
{
  "input": "Compare current evidence on grid-scale batteries.",
  "mode": "research",
  "grounding": {
    "search": true,
    "minimum_sources": 2
  }
}
```

When grounding is requested, the API retrieves evidence before model invocation. It supplies labelled excerpts such as `[S1]` and instructs the model to cite only those labels. The API maps used labels back to source records and reports unknown labels as invalid references.

Grounding states:
- `grounded`: the requested minimum number of evidence records was retrieved.
- `insufficient_sources`: some evidence was retrieved, but fewer than requested.
- `no_results`: the retrieval paths returned no evidence.
- `not_requested`: grounding was explicitly disabled.

Citation validation states:
- `valid`: no unknown source labels were used.
- `no_citations`: evidence was supplied but the model cited none.
- `invalid_references`: the model used one or more labels that were not supplied.

A valid label only proves that the label maps to a retrieved result. It does not prove that the cited page supports the associated claim. Semantic claim-to-source verification, source fetching, passage-level quotations and independent fact checking remain future work.

## Current limitations

- Semantic retrieval is optional and requires pgvector migration 005 plus an explicitly configured embedding provider. Lexical search remains available when it is disabled.
- External provider support currently includes the optional SerpApi Google adapter only.
- The external adapter returns search snippets, not full page contents.
- Ingestion is single-page and operator-triggered; recursive crawling, queue-backed workers, scheduled refresh, source approval console and automated rights review are not included.
- No publication date is invented; missing dates remain null.
- No independent semantic entailment check is performed on citations.
- The assistant remains non-streaming.
- External provider failures fail the grounded request rather than silently pretending that provider succeeded.

## Quality and safety gates before launch

- Apply migrations and test with an approved, rights-reviewed corpus.
- Add source-level ingestion and deletion workflows.
- Verify external provider plan, permitted use, retention and privacy requirements.
- Test query syntax, language matching, ranking, canonical URL normalisation and duplicate handling.
- Add claim-to-passage citation evaluation and adversarial citation tests.
- Add per-tenant quotas, search-provider spend controls, timeout budgets and audit records.
- Benchmark latency and retrieval relevance before adding vector search.


## Controlled single-page ingestion

Set `ORIOM7_INGESTION_TOKEN` in the API secret manager. Use a long random secret and never expose it to the web client. Requests must send it in `X-ORIOM7-INGESTION-TOKEN`.

### Register an approved source

`POST /v1/ingestion/sources`

```json
{
  "base_url": "https://publisher.example",
  "rights_basis": "Written licence permitting indexing and snippet display",
  "approval_reference": "LICENCE-2026-001",
  "approved_by": "content-operations"
}
```

### Ingest one page

`POST /v1/ingestion/crawl`

```json
{
  "url": "https://publisher.example/research/battery-storage",
  "language": "en"
}
```

The current worker:
- Requires an operator-registered HTTPS host and matches the requested host exactly.
- Checks DNS results are globally routable, checks the site's robots.txt for ORIOM7Bot, and refuses redirects.
- Accepts only HTML and plain text, with a 2 MB response cap and a 100,000-character extracted-text cap.
- Removes script/style and other non-content HTML elements before indexing.
- Stores a SHA-256 content hash, rights basis, robots decision, retrieval timestamp and ingestion-run outcome.
- Marks the previous version of a changed URL as deleted before indexing its replacement; unchanged pages update their fetch timestamp.

This is a controlled ingestion primitive, not yet a general web crawler. DNS is validated before the HTTP request, but the HTTP client resolves the hostname separately; production deployment must add network-level egress controls or pinned-address transport to close DNS-rebinding risk. Robots.txt is a crawl-policy signal, not a copyright licence. Source approval and the rights basis remain the operator's responsibility.


## Queue-backed distributed ingestion

Migration 004 adds a durable `search_crawl_jobs` queue and per-source crawl controls. Submit approved URLs through `POST /v1/ingestion/queue` using the operator token. The API only validates and enqueues; it does not fetch pages.

Run the independent worker process with `python worker.py` from `services/api`. Multiple workers can share the same PostgreSQL queue: claims use row locks with `SKIP LOCKED`, worker leases allow recovery after process crashes, and each source has a configurable minimum interval and rolling 24-hour page quota. Transient failures are retried with bounded exponential backoff; robots/policy and permanent content failures are not retried automatically. An operator can requeue a completed or terminal job by submitting the same URL again.

The worker is a deployable process, not a hosted service provisioned by this code change. Production still requires a supervisor, database capacity planning, queue metrics/alerts, tested backup/recovery, and network-level egress restrictions. Scheduled periodic discovery of new URLs and recursive link crawling are not yet included; the queue can be used for operator-submitted pages and reprocessing.


## Multilingual semantic retrieval

ORIOM7 now supports an optional pgvector semantic index alongside PostgreSQL lexical search. Both result lists are combined with reciprocal-rank fusion (RRF), which adds ranking contributions when the same canonical URL appears in multiple retrieval paths. Semantic matching is cross-language by default: the embedding model can retrieve a document in a different language from the query. Set `ORIOM7_SEMANTIC_LANGUAGE_FILTER=true` only when strict language filtering is required.

### Enable it

1. Confirm the managed PostgreSQL service supports the pgvector extension.
2. Apply `services/api/migrations/005_semantic_search.sql` after migrations 001–004.
3. Set these backend environment variables in the API and worker secret managers:

```bash
ORIOM7_SEMANTIC_SEARCH_ENABLED=true
ORIOM7_EMBEDDING_API_KEY=...
ORIOM7_EMBEDDING_BASE_URL=https://api.openai.com/v1
ORIOM7_EMBEDDING_MODEL=text-embedding-3-small
ORIOM7_SEMANTIC_LANGUAGE_FILTER=false
```

The initial adapter expects an OpenAI-compatible `POST /embeddings` endpoint returning 1,536-dimensional vectors. The default model is `text-embedding-3-small`. The adapter sends document text to the configured embedding provider; disclose this processing and confirm applicable data-processing, residency and retention terms before indexing private or licensed material. API keys are backend-only and are never returned to clients.

New pages processed by the queue worker receive embeddings when semantic search is enabled. Embedding failures do not discard the lexical document; they are logged and can be repaired by running the bounded backfill command:

```bash
cd services/api
python semantic_index.py
```

The backfill selects only eligible, non-deleted documents with an explicit rights basis and allowed/not-applicable robots status. It processes bounded batches and updates vectors when the content hash or embedding model changes. Backfill incurs provider usage/cost; estimate corpus size and enforce provider budgets before running it.

### Retrieval behaviour and limits

- The semantic index stores one vector per document and uses cosine-distance HNSW indexing.
- Lexical and semantic results are fused with RRF; external web results can also contribute.
- Semantic retrieval defaults to cross-language matching. This is model-dependent and must be benchmarked for each language and script before claiming language coverage.
- The current vector schema is fixed at 1,536 dimensions. A different embedding dimension requires a deliberate schema migration.
- This is document-level retrieval, not passage-level chunking. Long documents are embedded using the first 12,000 characters; passage chunking and citation-to-passage grounding remain future work.
- A vector similarity score measures embedding proximity, not factual correctness or source entailment.
- Search quality must be evaluated on representative multilingual query/document pairs, including dialects, transliteration, mixed-language queries and low-resource languages.
