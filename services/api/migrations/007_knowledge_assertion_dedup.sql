-- Keep repeated extraction runs idempotent for the same evidence and assertion.
CREATE UNIQUE INDEX IF NOT EXISTS knowledge_assertions_evidence_dedup_idx
ON knowledge_assertions (
    subject_entity_id, predicate, object_entity_id, evidence_document_id,
    md5(evidence_excerpt)
);
