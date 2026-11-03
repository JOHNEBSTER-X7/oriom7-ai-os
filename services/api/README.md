# ORIOM7 API Service

Runtime target: Python 3.12+ and FastAPI.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

The API starts with an in-memory accessibility-profile store when `DATABASE_URL` is unset and `ORIOM7_ENV` is not `production`. This is for local development and tests only; profiles are lost on restart.

For durable storage, apply `migrations/001_accessibility_profiles.sql`, set `DATABASE_URL`, then start the API. Production startup deliberately fails without `DATABASE_URL`.

## Authentication integration

The accessibility routes derive the profile owner from `request.state.user_id`, which must be set by trusted OIDC/session authentication middleware. They do not accept a user ID from the request body.

For local-only testing, set `ORIOM7_ALLOW_DEV_USER_HEADER=true` and send `X-ORIOM7-DEV-USER`. Never enable this option in a public or production deployment. The repository does not yet include a complete OIDC provider integration.

## Accessibility endpoints

- `GET /v1/accessibility/profile`
- `PUT /v1/accessibility/profile`
- `DELETE /v1/accessibility/profile`
- `POST /v1/accessibility/resolve` (temporary overrides; never persisted)

The profile stores functional preferences, not diagnoses or inferred health information.

## Tests

```bash
pip install -r requirements-dev.txt
PYTHONPATH=. pytest -q
```

Apply migrations `001_accessibility_profiles.sql` through `004_distributed_crawl_queue.sql` in order before using persistent search, ingestion and queued workers. Search now uses the PostgreSQL lexical index and optional external search adapters; see [Hybrid Search and Grounding](../../docs/HYBRID_SEARCH_AND_GROUNDING.md). A controlled single-page ingestion endpoint is now available for operator-approved HTTPS hosts. It checks robots.txt, blocks redirects and non-public DNS targets, caps downloaded content, extracts text, records ingestion outcomes and indexes content only with the approved rights basis. Recursive crawling, queue-backed workers and scheduled refresh remain outstanding.


## Model providers and assistant generation

The API loads configured model providers during startup. See [Model Provider Configuration](../../docs/MODEL_PROVIDER_CONFIGURATION.md) for environment variables, explicit model IDs, primary/fallback routing and pricing configuration.

- `GET /v1/models` — authenticated catalogue of configured model IDs and enabled capabilities.
- `POST /v1/assistant/responses` — authenticated non-streaming generation endpoint.

Set provider secrets in the deployment secret manager. A provider is enabled only when both its API key and explicit model ID are configured. The initial adapters use the OpenAI Responses API-compatible contract, including DeepSeek's documented Responses endpoint.

The assistant endpoint applies the saved accessibility profile. It returns token usage and provider metadata, with estimated cost only when configured rates are supplied. It does not yet connect to hybrid retrieval, citation verification, tool execution, streaming or durable conversation history; the response explicitly identifies grounding as not connected.


## Controlled search ingestion

Configure `ORIOM7_INGESTION_TOKEN` as a long random secret in the API secret manager. Do not expose it in the browser application. The ingestion routes use the `X-ORIOM7-INGESTION-TOKEN` header and require a configured database pool.

- `POST /v1/ingestion/sources` — register an HTTPS host with a documented rights basis, approval reference and approving operator.
- `POST /v1/ingestion/crawl` — fetch and index one URL on an approved host.

The initial crawler is deliberately single-page: it does not follow links or redirects, accepts only HTTPS on port 443, checks public DNS resolution and robots.txt, accepts HTML/plain text only, and caps page downloads at 2 MB. It records indexed/unchanged/blocked/failed outcomes. The ingestion token is an operator credential, not a replacement for an enterprise identity and role-management system.

A host registration is an operator attestation. Confirm licence/terms, privacy, copyright, retention and deletion permissions before registering a source. Deploy network-level egress restrictions as an additional SSRF defence, because DNS validation at application level cannot guarantee address pinning across a later HTTP connection.


## Controlled search ingestion

Configure `ORIOM7_INGESTION_TOKEN` as a long random secret in the API secret manager. Do not expose it in the browser application. The ingestion routes use the `X-ORIOM7-INGESTION-TOKEN` header and require a configured database pool.

- `POST /v1/ingestion/sources` — register an HTTPS host with a documented rights basis, approval reference and approving operator.
- `POST /v1/ingestion/crawl` — fetch and index one URL on an approved host.

The initial crawler is deliberately single-page: it does not follow links or redirects, accepts only HTTPS on port 443, checks public DNS resolution and robots.txt, accepts HTML/plain text only, and caps page downloads at 2 MB. It records indexed/unchanged/blocked/failed outcomes. The ingestion token is an operator credential, not a replacement for an enterprise identity and role-management system.

A host registration is an operator attestation. Confirm licence/terms, privacy, copyright, retention and deletion permissions before registering a source. Deploy network-level egress restrictions as an additional SSRF defence, because DNS validation at application level cannot guarantee address pinning across a later HTTP connection.


## Distributed crawl workers

Apply `004_distributed_crawl_queue.sql` after migration 003. The API exposes `POST /v1/ingestion/queue`, protected by `X-ORIOM7-INGESTION-TOKEN`; it validates that the exact HTTPS host is registered and approved, then stores a durable queue job without fetching the page in the API process.

Run one or more independent worker processes from `services/api`:

```bash
python worker.py
```

Each worker claims jobs using PostgreSQL row locks and `SKIP LOCKED`, records a lease, checks source approval again, enforces per-source request spacing and a rolling 24-hour page quota, checks robots.txt, and indexes the page. Expired worker leases can be reclaimed. Transient failures use bounded exponential retry; policy/content failures are terminal until an operator explicitly requeues the page. Repeated queue requests refresh terminal/completed jobs.

Worker settings:
- `DATABASE_URL` — required.
- `ORIOM7_CRAWL_WORKER_ID` — optional worker identifier; defaults to hostname.
- `ORIOM7_CRAWL_IDLE_SECONDS` — idle polling interval; defaults to 3 seconds.

Run workers as a separately supervised service (for example, a container or process manager), not inside the FastAPI web process. Configure database backups, metrics, queue-age alerts and network egress controls before production use. A worker fleet is not automatically provisioned by this repository change.


## Multilingual semantic search

Semantic retrieval is optional. The PostgreSQL target must support pgvector; apply `migrations/005_semantic_search.sql` after migrations 001–004. Set `ORIOM7_SEMANTIC_SEARCH_ENABLED=true` and configure `ORIOM7_EMBEDDING_API_KEY`, `ORIOM7_EMBEDDING_BASE_URL` and `ORIOM7_EMBEDDING_MODEL` in the API and worker secret managers. Defaults are the OpenAI embeddings endpoint and `text-embedding-3-small` (1,536 dimensions). Never expose embedding credentials to the web client.

When enabled, search combines PostgreSQL lexical results with pgvector cosine similarity using reciprocal-rank fusion. Semantic retrieval is cross-language by default; set `ORIOM7_SEMANTIC_LANGUAGE_FILTER=true` to constrain results to the requested language. This depends on embedding-model quality and must be evaluated per language before advertising coverage.

The queue worker embeds new/updated pages. To populate the existing eligible corpus, run `python semantic_index.py` from this directory. The backfill sends up to 12,000 characters per document to the configured embedding provider in batches. It only processes indexed, non-deleted documents with a non-empty rights basis and an allowed/not-applicable robots status. Review data-processing terms and provider costs first.

Vectors are document-level, fixed at 1,536 dimensions and do not establish factual support. Passage chunking, claim-to-passage verification and multilingual evaluation benchmarks remain future work. Lexical search remains available when semantic search is disabled.
