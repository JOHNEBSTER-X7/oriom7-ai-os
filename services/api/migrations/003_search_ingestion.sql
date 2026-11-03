-- Controlled ORIOM7 source registry and ingestion audit trail.
CREATE TABLE IF NOT EXISTS search_sources (
    source_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    base_url TEXT NOT NULL UNIQUE,
    host TEXT NOT NULL,
    rights_basis TEXT NOT NULL CHECK (btrim(rights_basis) <> ''),
    approval_reference TEXT NOT NULL CHECK (btrim(approval_reference) <> ''),
    approved_by TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'approved'
        CHECK (status IN ('approved', 'paused', 'revoked')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS search_ingestion_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES search_sources(source_id),
    requested_url TEXT NOT NULL,
    final_url TEXT,
    outcome TEXT NOT NULL CHECK (outcome IN ('indexed', 'unchanged', 'blocked', 'rejected', 'failed')),
    detail TEXT,
    document_id UUID REFERENCES search_documents(document_id),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS search_sources_status_idx ON search_sources(status);
CREATE INDEX IF NOT EXISTS search_ingestion_runs_source_time_idx
    ON search_ingestion_runs(source_id, started_at DESC);
