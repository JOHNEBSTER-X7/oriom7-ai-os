-- ORIOM7 LAB OS: persistent research projects, experiments, event history and equipment.
-- Apply after the existing numbered migrations. Data is user-scoped by trusted auth subject.

CREATE TABLE IF NOT EXISTS lab_projects (
    project_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_subject TEXT NOT NULL,
    title TEXT NOT NULL CHECK (char_length(title) BETWEEN 3 AND 160),
    description TEXT,
    discipline TEXT NOT NULL DEFAULT 'other'
        CHECK (discipline IN (
            'ai','semiconductors','computing','robotics','automotive','networking',
            'cybersecurity','materials','energy','aerospace','biotechnology',
            'healthcare','manufacturing','agriculture','mining','fintech',
            'commerce','other'
        )),
    objectives JSONB NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(objectives) = 'array'),
    status TEXT NOT NULL DEFAULT 'planning'
        CHECK (status IN ('planning','active','paused','completed','archived')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (project_id, owner_subject)
);

CREATE INDEX IF NOT EXISTS lab_projects_owner_updated_idx
    ON lab_projects (owner_subject, updated_at DESC);
CREATE INDEX IF NOT EXISTS lab_projects_owner_discipline_status_idx
    ON lab_projects (owner_subject, discipline, status);

CREATE TABLE IF NOT EXISTS lab_experiments (
    experiment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL,
    owner_subject TEXT NOT NULL,
    title TEXT NOT NULL CHECK (char_length(title) BETWEEN 3 AND 160),
    hypothesis TEXT,
    protocol TEXT,
    configuration JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(configuration) = 'object'),
    status TEXT NOT NULL DEFAULT 'planned'
        CHECK (status IN ('planned','queued','running','completed','failed','cancelled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (experiment_id, owner_subject),
    FOREIGN KEY (project_id, owner_subject)
        REFERENCES lab_projects (project_id, owner_subject)
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS lab_experiments_project_updated_idx
    ON lab_experiments (project_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS lab_experiments_owner_status_idx
    ON lab_experiments (owner_subject, status, updated_at DESC);

CREATE TABLE IF NOT EXISTS lab_experiment_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID NOT NULL,
    owner_subject TEXT NOT NULL,
    event_type TEXT NOT NULL
        CHECK (event_type IN (
            'note','protocol_update','status_change','measurement',
            'result_summary','deviation','review'
        )),
    summary TEXT NOT NULL CHECK (char_length(summary) BETWEEN 3 AND 1000),
    data JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(data) = 'object'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (experiment_id, owner_subject)
        REFERENCES lab_experiments (experiment_id, owner_subject)
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS lab_experiment_events_timeline_idx
    ON lab_experiment_events (experiment_id, created_at ASC);
CREATE INDEX IF NOT EXISTS lab_experiment_events_owner_idx
    ON lab_experiment_events (owner_subject, created_at DESC);

-- Event history is append-only. Corrections are new events, not destructive edits.
CREATE OR REPLACE FUNCTION prevent_lab_event_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'lab experiment events are append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS lab_experiment_events_no_update ON lab_experiment_events;
CREATE TRIGGER lab_experiment_events_no_update
    BEFORE UPDATE OR DELETE ON lab_experiment_events
    FOR EACH ROW EXECUTE FUNCTION prevent_lab_event_mutation();

CREATE TABLE IF NOT EXISTS lab_equipment (
    equipment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_subject TEXT NOT NULL,
    name TEXT NOT NULL CHECK (char_length(name) BETWEEN 2 AND 160),
    category TEXT NOT NULL CHECK (char_length(category) BETWEEN 2 AND 80),
    manufacturer TEXT,
    model TEXT,
    asset_tag TEXT,
    location TEXT,
    status TEXT NOT NULL DEFAULT 'available'
        CHECK (status IN ('available','in_use','maintenance','retired')),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(metadata) = 'object'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS lab_equipment_owner_asset_tag_unique
    ON lab_equipment (owner_subject, asset_tag)
    WHERE asset_tag IS NOT NULL;
CREATE INDEX IF NOT EXISTS lab_equipment_owner_status_idx
    ON lab_equipment (owner_subject, status, name);

COMMENT ON TABLE lab_projects IS
    'ORIOM7 LAB OS research projects; owner_subject comes from trusted authentication middleware.';
COMMENT ON TABLE lab_experiments IS
    'Versionable experiment definitions; physical experiment execution is not controlled by this API.';
COMMENT ON TABLE lab_experiment_events IS
    'Append-only experiment activity, measurement, review and status history.';
COMMENT ON TABLE lab_equipment IS
    'User-scoped laboratory equipment register; status updates do not actuate equipment.';
