-- Optional multilingual semantic retrieval using pgvector.
-- The target PostgreSQL service must support the pgvector extension.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS search_document_embeddings (
    document_id UUID PRIMARY KEY REFERENCES search_documents(document_id) ON DELETE CASCADE,
    embedding_model TEXT NOT NULL,
    embedding vector(1536) NOT NULL,
    content_hash TEXT NOT NULL,
    embedded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS search_document_embeddings_hnsw_idx
    ON search_document_embeddings USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS search_document_embeddings_model_idx
    ON search_document_embeddings (embedding_model);
