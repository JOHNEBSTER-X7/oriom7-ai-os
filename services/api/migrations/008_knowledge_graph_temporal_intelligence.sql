-- Temporal validity for sourced relationships. NULL means unknown/open bound.
ALTER TABLE knowledge_assertions
    ADD COLUMN IF NOT EXISTS valid_from DATE,
    ADD COLUMN IF NOT EXISTS valid_to DATE;

ALTER TABLE knowledge_assertions
    DROP CONSTRAINT IF EXISTS knowledge_assertions_validity_range_check;
ALTER TABLE knowledge_assertions
    ADD CONSTRAINT knowledge_assertions_validity_range_check
    CHECK (valid_from IS NULL OR valid_to IS NULL OR valid_from <= valid_to);

CREATE INDEX IF NOT EXISTS knowledge_assertions_temporal_idx
    ON knowledge_assertions (subject_entity_id, predicate, valid_from, valid_to)
    WHERE status = 'accepted';
