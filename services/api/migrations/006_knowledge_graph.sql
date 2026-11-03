-- ORIOM7 evidence-linked knowledge graph foundation.
CREATE TABLE IF NOT EXISTS knowledge_entities (
    entity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type TEXT NOT NULL CHECK (entity_type ~ '^[a-z][a-z0-9_]{1,39}$'),
    canonical_name TEXT NOT NULL,
    normalised_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (entity_type, normalised_name)
);

CREATE TABLE IF NOT EXISTS knowledge_entity_aliases (
    alias_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID NOT NULL REFERENCES knowledge_entities(entity_id) ON DELETE CASCADE,
    alias TEXT NOT NULL,
    normalised_alias TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (entity_id, normalised_alias)
);
CREATE INDEX IF NOT EXISTS knowledge_entity_alias_lookup_idx
    ON knowledge_entity_aliases (normalised_alias);

CREATE TABLE IF NOT EXISTS knowledge_assertions (
    assertion_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_entity_id UUID NOT NULL REFERENCES knowledge_entities(entity_id),
    predicate TEXT NOT NULL CHECK (predicate ~ '^[a-z][a-z0-9_]{1,79}$'),
    object_entity_id UUID NOT NULL REFERENCES knowledge_entities(entity_id),
    evidence_document_id UUID NOT NULL REFERENCES search_documents(document_id),
    evidence_excerpt TEXT NOT NULL CHECK (length(evidence_excerpt) BETWEEN 20 AND 2000),
    confidence DOUBLE PRECISION NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    extraction_method TEXT NOT NULL DEFAULT 'human_or_model_candidate',
    status TEXT NOT NULL DEFAULT 'unverified'
        CHECK (status IN ('unverified', 'accepted', 'rejected', 'superseded')),
    submitted_by TEXT NOT NULL,
    reviewed_by TEXT,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (subject_entity_id <> object_entity_id)
);

CREATE INDEX IF NOT EXISTS knowledge_assertions_subject_idx
    ON knowledge_assertions (subject_entity_id, predicate, status);
CREATE INDEX IF NOT EXISTS knowledge_assertions_object_idx
    ON knowledge_assertions (object_entity_id, predicate, status);
CREATE INDEX IF NOT EXISTS knowledge_assertions_evidence_idx
    ON knowledge_assertions (evidence_document_id);
CREATE INDEX IF NOT EXISTS knowledge_assertions_status_idx
    ON knowledge_assertions (status, created_at DESC);

COMMENT ON TABLE knowledge_assertions IS
    'Provenance-bearing relationship claims. Only accepted assertions may be exposed as graph facts.';
