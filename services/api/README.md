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

Apply migrations 001–007 in numerical order before using all persistent search, semantic retrieval, queued ingestion and knowledge graph features. See [Hybrid Search and Grounding](../../docs/HYBRID_SEARCH_AND_GROUNDING.md) and [Knowledge Graph Foundation](../../docs/KNOWLEDGE_GRAPH_FOUNDATION.md). Controlled single-page ingestion and a PostgreSQL-backed queue worker are implemented; recursive link discovery and scheduled URL discovery are not.


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


## Evidence-linked knowledge graph

Apply migrations 006–008 after migrations 001–005. Migration 008 adds optional temporal validity dates to assertions. The API provides candidate submission, token-protected human review, entity/alias lookup, one-hop graph reads, duplicate-identity suggestions, potential-conflict triage and bounded multi-hop paths:

- `POST /v1/knowledge/observations`
- `POST /v1/knowledge/assertions/{assertion_id}/review`
- `GET /v1/knowledge/entities?q=...`
- `GET /v1/knowledge/entities/{entity_id}`
- `GET /v1/knowledge/entities/{entity_id}/resolution-candidates`
- `GET /v1/knowledge/assertions/potential-conflicts?predicate=...&single_valued=true`
- `GET /v1/knowledge/entities/{entity_id}/paths?max_depth=2&as_of=YYYY-MM-DD`
- `POST /v1/knowledge/documents/{document_id}/extract`

Assertions may include `valid_from` and `valid_to` when dates are explicitly supported by source evidence. Unknown bounds remain null. Multi-hop traversal is limited to depth 1–3 and includes evidence for every edge. Optional `as_of` filters relationships by their recorded validity window.

Resolution candidates are similarity-ranked suggestions only; ORIOM7 does not merge entities automatically. Potential conflicts are returned only when the caller explicitly confirms the predicate should be single-valued; overlapping accepted claims with different objects are flagged for human assessment, not automatically labelled false. Multi-valued relationships must not be analysed as single-valued.

Every assertion must reference eligible indexed evidence. Submitted and extracted assertions remain `unverified`; graph reads return accepted assertions only. Set `ORIOM7_GRAPH_REVIEW_TOKEN` in backend secrets to enable review. The model extraction endpoint requires a configured provider and the optional worker hook remains disabled by default. These capabilities are research and review aids, not automated fact verification. See [Knowledge Graph Foundation](../../docs/KNOWLEDGE_GRAPH_FOUNDATION.md).


## Research agent worker

Run `python worker.py` as a separate supervised process. Apply migrations 001–010 first. The worker processes approved crawl jobs and durable research-agent jobs, and enqueues due recurring schedules. Configure the worker with DATABASE_URL, model provider credentials and search provider credentials. Without a configured model provider, research jobs cannot execute.

## ORIOM7 LAB OS foundation

The first LAB OS API slice provides authenticated, owner-scoped research project,
experiment, append-only experiment-event and equipment-register endpoints.

Endpoints:
- `POST /v1/labs/projects` — create a research project.
- `GET /v1/labs/projects` — list the authenticated user's projects.
- `GET /v1/labs/projects/{project_id}` — retrieve an owned project.
- `PATCH /v1/labs/projects/{project_id}` — update project lifecycle status.
- `POST /v1/labs/projects/{project_id}/experiments` — register an experiment plan.
- `GET /v1/labs/projects/{project_id}/experiments` — list experiments for an owned project.
- `GET /v1/labs/experiments/{experiment_id}` — retrieve an owned experiment.
- `POST /v1/labs/experiments/{experiment_id}/events` — append a note, protocol update, status change, measurement, result summary, deviation or review event.
- `GET /v1/labs/experiments/{experiment_id}/events` — read the experiment event history.
- `POST /v1/labs/equipment` — register equipment metadata.
- `GET /v1/labs/equipment` — list registered equipment.
- `PATCH /v1/labs/equipment/{equipment_id}` — update equipment register status.

Apply `migrations/011_lab_os.sql` after migrations 001–007. The API requires
the existing trusted authentication middleware and a configured PostgreSQL
`DATABASE_URL`; there is deliberately no in-memory fallback for laboratory
records. User identity is derived from trusted middleware, never from request
payloads. Project and experiment ownership is enforced in application queries
and by composite database foreign keys.

Experiment events are append-only. Corrections should be recorded as new events.
Status transitions are constrained: planned → queued/cancelled; queued →
running/cancelled; running → completed/failed/cancelled. Terminal states cannot
be reopened through the event API.

This foundation is a research-management system only. It does not actuate
equipment, schedule physical experiments, verify scientific results, provide
laboratory safety certification or replace calibrated instruments and local
operating procedures. Those capabilities require separately designed and
validated integrations, human approval and safety controls.


### ORIOM7 Digital Notebook

Apply `migrations/012_lab_digital_notebook.sql` after migration 011. The notebook adds project-linked research records with optional experiment linkage:

- `POST /v1/labs/projects/{project_id}/notebook` — append a note, hypothesis, observation, measurement, result, decision, protocol, review or deviation.
- `GET /v1/labs/projects/{project_id}/notebook` — retrieve the chronological notebook, with optional `entry_type` and `experiment_id` filters.

Entries are attributed to the authenticated subject; the client cannot supply an owner identity. Entries are append-only at the database layer: corrections are new entries that should reference the original record in their content/metadata. Content is limited to 20,000 characters and metadata to 16 KB. This is an auditable application record, not a qualified electronic-signature system, regulated clinical record, validated laboratory information management system (LIMS), or guarantee of scientific integrity. Retention, backup, access review and regulatory validation remain deployment responsibilities.


### ORIOM7 Equipment Manager

Apply `migrations/013_equipment_manager.sql` after migration 012. The Equipment Manager extends the original equipment register with append-only calibration and maintenance records and a reservation schedule.

- `POST /v1/labs/equipment/{equipment_id}/calibrations` and `GET /v1/labs/equipment/{equipment_id}/calibrations` — record and list calibration history, due dates, outcomes and certificate references.
- `POST /v1/labs/equipment/{equipment_id}/maintenance` and `GET /v1/labs/equipment/{equipment_id}/maintenance` — record and list preventive/corrective maintenance, inspections and next-due dates.
- `POST /v1/labs/equipment/{equipment_id}/bookings` and `GET /v1/labs/equipment/{equipment_id}/bookings` — create and list equipment reservations.
- `PATCH /v1/labs/equipment/bookings/{booking_id}` — cancel or complete an active reservation.
- `GET /v1/labs/equipment/summary` — owner-scoped asset, calibration, maintenance and booking counters.
- `GET /v1/labs/equipment/summary` — owner-scoped asset, calibration, maintenance and booking counters.

All operations are scoped to the authenticated owner. Booking creation locks the equipment row and rejects overlapping confirmed reservations; equipment in maintenance or retired status cannot be booked. A failed or conditional calibration automatically moves the asset into maintenance and cancels its active/future confirmed bookings. An asset cannot be returned to available/in-use while its latest calibration has failed, is conditional, or is overdue. Equipment cannot be moved into maintenance/retired while a confirmed booking remains active. Calibration and maintenance history is append-only. Calibration records are evidence supplied by the operator, not independent accreditation or certification. The booking system does not control instruments, guarantee room/facility availability, or replace local safety and authorisation checks.
