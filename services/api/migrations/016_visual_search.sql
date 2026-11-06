-- Customer-owned visual vectors. Raw image bytes are never stored in this table.
CREATE TABLE IF NOT EXISTS visual_search_items (
    visual_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id TEXT NOT NULL,
    label TEXT NOT NULL CHECK (length(btrim(label)) BETWEEN 1 AND 240),
    content_sha256 CHAR(64) NOT NULL,
    embedding_model TEXT NOT NULL,
    embedding_dimensions INTEGER NOT NULL CHECK (embedding_dimensions BETWEEN 1 AND 16000),
    embedding vector NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (vector_dims(embedding) = embedding_dimensions)
);
CREATE INDEX IF NOT EXISTS visual_search_items_owner_model_idx
    ON visual_search_items (owner_id, embedding_model, embedding_dimensions);
CREATE INDEX IF NOT EXISTS visual_search_items_hnsw_idx
    ON visual_search_items USING hnsw (embedding vector_cosine_ops)
    WHERE embedding_dimensions <= 2000;
