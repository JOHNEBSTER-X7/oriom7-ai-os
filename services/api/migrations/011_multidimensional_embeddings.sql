-- Enable multiple embedding models and dimensions per document.
-- Existing 1,536-dimensional vectors and model rows are preserved.
ALTER TABLE search_document_embeddings
    ALTER COLUMN embedding TYPE vector USING embedding::vector;

ALTER TABLE search_document_embeddings
    ADD COLUMN IF NOT EXISTS embedding_dimensions INTEGER;

UPDATE search_document_embeddings
SET embedding_dimensions = vector_dims(embedding)
WHERE embedding_dimensions IS NULL;

ALTER TABLE search_document_embeddings
    ALTER COLUMN embedding_dimensions SET NOT NULL;

ALTER TABLE search_document_embeddings
    DROP CONSTRAINT IF EXISTS search_document_embeddings_pkey;

ALTER TABLE search_document_embeddings
    ADD CONSTRAINT search_document_embeddings_pkey
    PRIMARY KEY (document_id, embedding_model);

DROP INDEX IF EXISTS search_document_embeddings_hnsw_idx;

-- HNSW indexing for pgvector's vector type supports up to 2,000 dimensions.
-- Higher dimensions remain searchable by exact cosine ranking.
CREATE INDEX search_document_embeddings_hnsw_idx
    ON search_document_embeddings USING hnsw (embedding vector_cosine_ops)
    WHERE embedding_dimensions <= 2000;

CREATE INDEX IF NOT EXISTS search_document_embeddings_model_dimensions_idx
    ON search_document_embeddings (embedding_model, embedding_dimensions);
