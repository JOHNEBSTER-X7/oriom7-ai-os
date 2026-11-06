# ORIOM7 API Service

Runtime target: Python 3.12+ and FastAPI.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

The API uses an in-memory accessibility-profile store only for local development when DATABASE_URL is unset. Production startup deliberately fails without DATABASE_URL.

## Authentication integration

Accessibility routes derive the profile owner from trusted authentication middleware via request.state.user_id. For local-only testing, ORIOM7_ALLOW_DEV_USER_HEADER=true enables X-ORIOM7-DEV-USER. Never enable this in production. A complete OIDC provider integration remains deployment work.

## Main API areas

- Accessibility preferences and response adaptation.
- Hybrid search: POST /v1/search.
- Controlled source registration and ingestion.
- Evidence-linked knowledge graph and human review.
- Research workspace and durable autonomous research jobs.
- Model catalogue and assistant generation.

## Tests

```bash
pip install -r requirements-dev.txt
PYTHONPATH=. pytest -q
```

Apply database migrations in numerical order, 001–011, before using all persistent search, vector retrieval, ingestion, knowledge graph and research-worker features.

## Semantic and multidimensional vector search

The PostgreSQL target must support pgvector. Apply migrations 001–011 in numerical order. Migration 011 converts the original fixed 1,536-dimensional column to a dimension-aware vector column while preserving existing vectors.

Configure these values in the API and worker secret managers:

- ORIOM7_SEMANTIC_SEARCH_ENABLED=true
- ORIOM7_EMBEDDING_API_KEY
- ORIOM7_EMBEDDING_BASE_URL (defaults to the OpenAI API base URL)
- ORIOM7_EMBEDDING_MODEL
- ORIOM7_EMBEDDING_DIMENSIONS (defaults to 1536)

The selected model/provider must support the configured output dimension. Each stored embedding records its model and dimension. Multiple models can coexist for one source document; vectors are compared only when both model and dimension match. ORIOM7 never pads, truncates or mixes incompatible vectors.

pgvector vector storage supports up to 16,000 dimensions. HNSW vector indexing is used up to 2,000 dimensions; above that, ORIOM7 uses exact cosine ranking, which is correct but more computationally expensive. This is a practical storage/indexing limit, not a mathematical maximum.

Keep the existing 1,536-dimensional setting for the first migration and regression check. Back up the database, apply migration 011, run the tests, and then change model/dimension only after confirming provider support. Run python semantic_index.py from this directory to backfill the configured model/dimension over eligible indexed documents.

Embedding requests transmit bounded document text to the configured provider. Confirm data-processing terms, privacy, retention, data residency, deletion obligations and cost before enabling a provider. Embeddings represent similarity; they are not proof of factual support. Preserve source provenance and evidence review.

## Workers and ingestion governance

Run python worker.py as a separately supervised process after applying migrations 001–011. Register only sources whose terms, licence, privacy, retention and deletion permissions have been reviewed. The source registry's approval fields are operator attestations, not independent legal approval.
