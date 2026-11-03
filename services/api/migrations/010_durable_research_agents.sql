-- Durably enqueue research work and maintain optional recurring objectives.

ALTER TABLE research_agent_runs
    DROP CONSTRAINT IF EXISTS research_agent_runs_status_check;
ALTER TABLE research_agent_runs
    ADD CONSTRAINT research_agent_runs_status_check
    CHECK (status IN ('queued', 'running', 'completed', 'partial', 'failed', 'cancelled'));

CREATE TABLE IF NOT EXISTS research_agent_jobs (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL UNIQUE REFERENCES research_agent_runs(run_id) ON DELETE CASCADE,
    owner_subject TEXT NOT NULL,
    payload JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    max_attempts INTEGER NOT NULL DEFAULT 3 CHECK (max_attempts BETWEEN 1 AND 5),
    available_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    locked_at TIMESTAMPTZ,
    locked_by TEXT,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS research_agent_jobs_claim_idx
    ON research_agent_jobs (status, available_at, created_at);
CREATE INDEX IF NOT EXISTS research_agent_jobs_owner_idx
    ON research_agent_jobs (owner_subject, created_at DESC);

CREATE TABLE IF NOT EXISTS research_agent_schedules (
    schedule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_subject TEXT NOT NULL,
    research_question TEXT NOT NULL CHECK (length(research_question) BETWEEN 8 AND 2000),
    interval_minutes INTEGER NOT NULL CHECK (interval_minutes BETWEEN 60 AND 43200),
    max_sources INTEGER NOT NULL DEFAULT 12 CHECK (max_sources BETWEEN 3 AND 30),
    extract_graph_candidates BOOLEAN NOT NULL DEFAULT FALSE,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    next_run_at TIMESTAMPTZ NOT NULL,
    last_run_id UUID REFERENCES research_agent_runs(run_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS research_agent_schedules_due_idx
    ON research_agent_schedules (enabled, next_run_at);
