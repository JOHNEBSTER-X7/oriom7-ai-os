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

Search and assistant orchestration remain separate product work. Do not run long crawling or indexing jobs in HTTP handlers; dispatch them to managed queues and workers.


## Model providers and assistant generation

The API loads configured model providers during startup. See [Model Provider Configuration](../../docs/MODEL_PROVIDER_CONFIGURATION.md) for environment variables, explicit model IDs, primary/fallback routing and pricing configuration.

- `GET /v1/models` — authenticated catalogue of configured model IDs and enabled capabilities.
- `POST /v1/assistant/responses` — authenticated non-streaming generation endpoint.

Set provider secrets in the deployment secret manager. A provider is enabled only when both its API key and explicit model ID are configured. The initial adapters use the OpenAI Responses API-compatible contract, including DeepSeek's documented Responses endpoint.

The assistant endpoint applies the saved accessibility profile. It returns token usage and provider metadata, with estimated cost only when configured rates are supplied. It does not yet connect to hybrid retrieval, citation verification, tool execution, streaming or durable conversation history; the response explicitly identifies grounding as not connected.
