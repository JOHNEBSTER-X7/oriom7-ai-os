# ORIOM7 Visual Similarity Search V1

This milestone adds owner-scoped image-to-image similarity retrieval.

## Endpoints

- `POST /v1/vision/index` — multipart image plus required `label`; creates a visual embedding record.
- `POST /v1/vision/search` — multipart query image plus optional `limit` (1–50); returns ranked similar labels and cosine similarity.
- `DELETE /v1/vision/index/{item_id}` — deletes an item belonging to the authenticated API-key owner.

All routes require a valid ORIOM7 developer API key. Similarity searches are strictly scoped to the key owner's account, embedding model and vector dimensions.

## Provider configuration

Configure a trusted HTTPS JSON endpoint:

- `ORIOM7_VISUAL_EMBEDDING_ENDPOINT` (required to enable)
- `ORIOM7_VISUAL_EMBEDDING_API_KEY` (optional)
- `ORIOM7_VISUAL_EMBEDDING_MODEL` (default `default`)
- `ORIOM7_VISUAL_EMBEDDING_DIMENSIONS` (default `1024`, range 1–16000)

The provider accepts JSON containing `model` and `image` with `media_type` and base64 `data_base64`. It returns an `embedding` numeric array with exactly the configured number of finite values. This is a separate provider from the visual question-answering endpoint; ORIOM7 does not assume the latter can create embeddings.

## Data and privacy

Image bytes are held in memory and forwarded to the configured embedding provider. They are not persisted by ORIOM7. The database stores only the vector, caller-supplied label, SHA-256 content hash, model/dimension metadata and account owner. No object storage is configured or required for this vector-only preview. Provider retention, privacy and processing-region terms must be reviewed before sensitive or regulated images are submitted.

The index is private to the API-key owner. Cross-account search is not supported. Deleting an item removes its vector record.

## Operational status

Migration `016_visual_search.sql` must be applied before use. Configure the provider before endpoints become available. This is an integration preview, not a claim of production-scale image understanding, video indexing, chart/map reasoning or cross-language visual descriptions.
