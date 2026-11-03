-- ORIOM7 first-party search index.
-- Only documents with an explicit rights_basis and indexed status are searchable.

CREATE TABLE IF NOT EXISTS search_documents (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_url TEXT NOT NULL,
    title TEXT NOT NULL,
    body_text TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'oriom7_index',
    language TEXT,
    region TEXT,
    publisher TEXT,
    published_at TIMESTAMPTZ,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    content_hash TEXT NOT NULL,
    rights_basis TEXT,
    robots_status TEXT NOT NULL DEFAULT 'not_checked'
        CHECK (robots_status IN ('allowed', 'blocked', 'not_checked', 'not_applicable')),
    index_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (index_status IN ('pending', 'indexed', 'rejected', 'failed')),
    search_vector TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('simple', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('simple', coalesce(body_text, '')), 'B')
    ) STORED,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (canonical_url, content_hash)
);

CREATE INDEX IF NOT EXISTS search_documents_vector_idx
    ON search_documents USING GIN (search_vector);

CREATE INDEX IF NOT EXISTS search_documents_status_fetched_idx
    ON search_documents (index_status, fetched_at DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS search_documents_language_idx
    ON search_documents (language)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS search_documents_url_idx
    ON search_documents (canonical_url);

COMMENT ON TABLE search_documents IS
    'Permission-aware ORIOM7 owned search index. Search excludes rows without rights_basis, non-indexed rows and deleted rows.';
