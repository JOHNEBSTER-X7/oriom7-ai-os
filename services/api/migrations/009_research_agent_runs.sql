-- Persist bounded autonomous research-agent runs and their evidence provenance.
CREATE TABLE IF NOT EXISTS research_agent_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_subject TEXT NOT NULL,
    research_question TEXT NOT NULL CHECK (length(research_question) BETWEEN 1 AND 2000),
    status TEXT NOT NULL CHECK (status IN ('running','completed','partial','failed')),
    plan JSONB NOT NULL DEFAULT '[]'::jsonb,
    result JSONB,
    error_code TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    CHECK (jsonb_typeof(plan) = 'array')
);
CREATE INDEX IF NOT EXISTS research_agent_runs_owner_idx
    ON research_agent_runs (owner_subject, started_at DESC);
