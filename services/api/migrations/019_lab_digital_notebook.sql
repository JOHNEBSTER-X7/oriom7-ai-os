-- ORIOM7 DIGITAL NOTEBOOK: project-linked, user-attributed append-only research records.
-- Apply after migration 018.

CREATE TABLE IF NOT EXISTS lab_notebook_entries (
    entry_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL,
    experiment_id UUID,
    owner_subject TEXT NOT NULL,
    entry_type TEXT NOT NULL CHECK (entry_type IN (
        'note','hypothesis','observation','measurement','result',
        'decision','protocol','review','deviation'
    )),
    title TEXT NOT NULL CHECK (char_length(title) BETWEEN 3 AND 180),
    content TEXT NOT NULL CHECK (char_length(content) BETWEEN 1 AND 20000),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(metadata) = 'object'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (project_id, owner_subject)
        REFERENCES lab_projects (project_id, owner_subject) ON DELETE RESTRICT,
    FOREIGN KEY (experiment_id, owner_subject)
        REFERENCES lab_experiments (experiment_id, owner_subject) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS lab_notebook_project_timeline_idx
    ON lab_notebook_entries (project_id, created_at ASC, entry_id ASC);
CREATE INDEX IF NOT EXISTS lab_notebook_project_type_idx
    ON lab_notebook_entries (project_id, entry_type, created_at DESC);
CREATE INDEX IF NOT EXISTS lab_notebook_experiment_timeline_idx
    ON lab_notebook_entries (experiment_id, created_at ASC)
    WHERE experiment_id IS NOT NULL;

CREATE OR REPLACE FUNCTION prevent_lab_notebook_entry_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'lab notebook entries are append-only; add a correction entry instead';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS lab_notebook_entries_no_update ON lab_notebook_entries;
CREATE TRIGGER lab_notebook_entries_no_update
    BEFORE UPDATE OR DELETE ON lab_notebook_entries
    FOR EACH ROW EXECUTE FUNCTION prevent_lab_notebook_entry_mutation();

COMMENT ON TABLE lab_notebook_entries IS
    'Append-only ORIOM7 research notebook. Corrections are new entries; ownership is derived from authenticated subject.';
