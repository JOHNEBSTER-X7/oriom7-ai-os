-- ORIOM7 LAB Quality, Compliance & Analytics.
-- Apply after 014_lab_inventory_procurement.sql. Owner-scoped and auditable records.

CREATE TABLE IF NOT EXISTS lab_quality_inspections (
  inspection_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lot_id UUID NOT NULL,
  owner_subject TEXT NOT NULL,
  inspection_type TEXT NOT NULL CHECK (char_length(inspection_type) BETWEEN 2 AND 100),
  outcome TEXT NOT NULL CHECK (outcome IN ('pass','fail','conditional')),
  sample_size INTEGER NOT NULL CHECK (sample_size > 0),
  defects_count INTEGER NOT NULL DEFAULT 0 CHECK (defects_count >= 0 AND defects_count <= sample_size),
  performed_by TEXT NOT NULL CHECK (char_length(performed_by) BETWEEN 2 AND 160),
  notes TEXT,
  evidence_reference TEXT,
  inspected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (inspection_id, owner_subject),
  FOREIGN KEY (lot_id, owner_subject)
    REFERENCES lab_inventory_lots(lot_id, owner_subject) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS lab_quality_inspections_lot_idx
  ON lab_quality_inspections(owner_subject, lot_id, inspected_at DESC);

CREATE TABLE IF NOT EXISTS lab_quality_nonconformances (
  nonconformance_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_subject TEXT NOT NULL,
  source_inspection_id UUID,
  title TEXT NOT NULL CHECK (char_length(title) BETWEEN 3 AND 180),
  description TEXT NOT NULL CHECK (char_length(description) BETWEEN 3 AND 4000),
  severity TEXT NOT NULL DEFAULT 'major' CHECK (severity IN ('minor','major','critical')),
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','investigating','capa_in_progress','verified','closed')),
  assigned_to TEXT,
  due_date DATE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (nonconformance_id, owner_subject),
  FOREIGN KEY (source_inspection_id, owner_subject)
    REFERENCES lab_quality_inspections(inspection_id, owner_subject) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS lab_quality_ncr_owner_status_idx
  ON lab_quality_nonconformances(owner_subject, status, created_at DESC);

CREATE TABLE IF NOT EXISTS lab_quality_capa_actions (
  action_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nonconformance_id UUID NOT NULL,
  owner_subject TEXT NOT NULL,
  action_type TEXT NOT NULL CHECK (action_type IN ('correction','corrective','preventive')),
  description TEXT NOT NULL CHECK (char_length(description) BETWEEN 3 AND 4000),
  assigned_to TEXT NOT NULL CHECK (char_length(assigned_to) BETWEEN 2 AND 160),
  due_date DATE,
  status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned','in_progress','completed','verified')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (action_id, owner_subject),
  FOREIGN KEY (nonconformance_id, owner_subject)
    REFERENCES lab_quality_nonconformances(nonconformance_id, owner_subject) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS lab_quality_capa_owner_status_idx
  ON lab_quality_capa_actions(owner_subject, status, due_date);

CREATE TABLE IF NOT EXISTS lab_quality_capa_events (
  event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  action_id UUID NOT NULL,
  owner_subject TEXT NOT NULL,
  event_type TEXT NOT NULL CHECK (event_type IN ('created','status_changed','note_added','verified')),
  from_status TEXT,
  to_status TEXT,
  note TEXT,
  recorded_by TEXT NOT NULL CHECK (char_length(recorded_by) BETWEEN 2 AND 160),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (action_id, owner_subject)
    REFERENCES lab_quality_capa_actions(action_id, owner_subject) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS lab_quality_capa_events_action_idx
  ON lab_quality_capa_events(owner_subject, action_id, created_at DESC);

CREATE TABLE IF NOT EXISTS lab_compliance_documents (
  document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_subject TEXT NOT NULL,
  supplier_id UUID,
  document_type TEXT NOT NULL CHECK (char_length(document_type) BETWEEN 2 AND 100),
  document_name TEXT NOT NULL CHECK (char_length(document_name) BETWEEN 2 AND 180),
  reference TEXT NOT NULL CHECK (char_length(reference) BETWEEN 2 AND 1000),
  issued_at DATE,
  expires_at DATE,
  review_status TEXT NOT NULL DEFAULT 'pending_review' CHECK (review_status IN ('pending_review','accepted','rejected','superseded')),
  reviewed_by TEXT,
  reviewed_at TIMESTAMPTZ,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (document_id, owner_subject),
  FOREIGN KEY (supplier_id, owner_subject)
    REFERENCES lab_inventory_suppliers(supplier_id, owner_subject) ON DELETE RESTRICT,
  CHECK (expires_at IS NULL OR issued_at IS NULL OR expires_at >= issued_at),
  CHECK ((review_status = 'pending_review' AND reviewed_at IS NULL) OR (review_status <> 'pending_review' AND reviewed_at IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS lab_compliance_documents_expiry_idx
  ON lab_compliance_documents(owner_subject, expires_at);

-- Inspection evidence and CAPA event history are append-only.
CREATE OR REPLACE FUNCTION prevent_lab_quality_record_mutation()
RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION 'quality evidence records are append-only'; END; $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS lab_quality_inspections_no_mutation ON lab_quality_inspections;
CREATE TRIGGER lab_quality_inspections_no_mutation
  BEFORE UPDATE OR DELETE ON lab_quality_inspections
  FOR EACH ROW EXECUTE FUNCTION prevent_lab_quality_record_mutation();
DROP TRIGGER IF EXISTS lab_quality_capa_events_no_mutation ON lab_quality_capa_events;
CREATE TRIGGER lab_quality_capa_events_no_mutation
  BEFORE UPDATE OR DELETE ON lab_quality_capa_events
  FOR EACH ROW EXECUTE FUNCTION prevent_lab_quality_record_mutation();

COMMENT ON TABLE lab_quality_inspections IS 'Append-only operator-entered inspection evidence; not independent certification.';
COMMENT ON TABLE lab_compliance_documents IS 'Document register and review metadata; not legal verification or proof of regulatory compliance.';
