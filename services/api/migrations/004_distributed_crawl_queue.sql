-- Durable queue and per-source crawl scheduling.
ALTER TABLE search_sources
    ADD COLUMN IF NOT EXISTS min_interval_seconds INTEGER NOT NULL DEFAULT 10
        CHECK (min_interval_seconds BETWEEN 1 AND 86400),
    ADD COLUMN IF NOT EXISTS next_allowed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS max_pages_per_day INTEGER NOT NULL DEFAULT 100
        CHECK (max_pages_per_day BETWEEN 1 AND 100000);

CREATE TABLE IF NOT EXISTS search_crawl_jobs (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES search_sources(source_id),
    url TEXT NOT NULL,
    language TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'blocked', 'rejected', 'failed')),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    max_attempts INTEGER NOT NULL DEFAULT 5 CHECK (max_attempts BETWEEN 1 AND 20),
    available_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    locked_at TIMESTAMPTZ,
    locked_by TEXT,
    last_error TEXT,
    document_id UUID REFERENCES search_documents(document_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source_id, url)
);

CREATE INDEX IF NOT EXISTS search_crawl_jobs_claim_idx
    ON search_crawl_jobs(status, available_at, created_at)
    WHERE status IN ('pending', 'running');
CREATE INDEX IF NOT EXISTS search_crawl_jobs_source_idx
    ON search_crawl_jobs(source_id, created_at DESC);
