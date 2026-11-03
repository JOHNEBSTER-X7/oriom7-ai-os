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

Apply migrations `001_accessibility_profiles.sql`, `002_search_index.sql` and `003_search_ingestion.sql` in order before using persistent search and ingestion. Apply migrations `001_accessibility_profiles.sql`, `002_search_index.sql` and `003_search_ingestion.sql` in order before using persistent search and ingestion. Search now uses the PostgreSQL lexical index and optional external search adapters; see [Hybrid Search and Grounding](../../docs/HYBRID_SEARCH_AND_GROUNDING.md). A controlled single-page ingestion endpoint is now available for operator-approved HTTPS hosts. It checks robots.txt, blocks redirects and non-public DNS targets, caps downloaded content, extracts text, records ingestion outcomes and indexes content only with the approved rights basis. Recursive crawling, queue-backed workers and scheduled refresh remain outstanding.


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
