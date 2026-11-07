# ORIOM7 Vector Retrieval and Embeddings

## Purpose

Extend ORIOM7's existing semantic search implementation without creating a separate vector product. Vector retrieval complements the existing PostgreSQL lexical index and external search adapters.

## Implemented design on this branch

- Configurable embedding output dimension via ORIOM7_EMBEDDING_DIMENSIONS.
- Backwards-compatible default of 1,536 dimensions.
- Model and dimension recorded with each stored vector.
- Composite identity (document_id, embedding_model, embedding_dimensions), allowing multiple model/dimension variants per document.
- Strict validation of vector length, numeric values and finite values.
- No padding, truncation or comparisons across different models/dimensions.
- HNSW cosine indexing for vectors up to 2,000 dimensions.
- Exact cosine ranking for dimensions above 2,000 and up to pgvector's 16,000-dimensional vector storage limit.
- Existing lexical, semantic and external result lists continue to be fused using reciprocal-rank fusion.

## Configuration

Set in the API and worker secret managers:

```dotenv
ORIOM7_SEMANTIC_SEARCH_ENABLED=true
ORIOM7_EMBEDDING_API_KEY=
ORIOM7_EMBEDDING_BASE_URL=https://api.openai.com/v1
ORIOM7_EMBEDDING_MODEL=text-embedding-3-small
ORIOM7_EMBEDDING_DIMENSIONS=1536
```

Choose a dimension explicitly supported by the selected model/provider. Some OpenAI-compatible providers do not implement the optional dimensions request parameter. The API must return vectors of exactly the configured size or ORIOM7 rejects the response.

## Database migration

Migration 011:

1. Converts the fixed vector(1536) column to an unconstrained vector column.
2. Adds and backfills embedding_dimensions from existing stored vectors.
3. Changes the primary key to (document_id, embedding_model, embedding_dimensions).
4. Rebuilds the HNSW index as a partial index for dimensions up to 2,000.
5. Adds a model/dimension lookup index.

Take a database backup before applying migrations. Apply migrations 001–011 in order. Existing 1,536-dimensional records are preserved.

## Performance characteristics

- Up to 2,000 dimensions: approximate nearest-neighbour retrieval through HNSW.
- 2,001–16,000 dimensions: exact cosine ranking. This avoids the HNSW dimension ceiling but may require more compute and latency as the corpus grows.
- Higher dimensions are not automatically better. Select model and dimension by retrieval-quality evaluation, latency, storage and provider cost.
- Do not mix dimensions or embedding models in one similarity calculation.

## Evaluation gates

Before enabling a new model/dimension in production, evaluate a rights-reviewed benchmark containing representative queries and documents from the verticals ORIOM7 actually indexes. Measure Recall@k, Precision@k, nDCG@k, MRR, latency, embedding cost, storage growth and cross-language performance. Compare against the existing 1,536-dimensional baseline and lexical-only retrieval.

## Data rights and factual reliability

Only eligible indexed documents with a documented rights basis and allowed/not-applicable robots status are embedded. Embedding requests send bounded document text to the configured provider. Review provider data-processing terms, privacy, retention, data residency and deletion requirements.

A vector similarity score indicates proximity in an embedding space, not truth, authority, freshness or factual support. Preserve source URLs, timestamps, retrieval provenance and evidence-review workflows.
