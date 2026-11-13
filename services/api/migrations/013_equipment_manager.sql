-- ORIOM7 Equipment Manager: calibration, maintenance and reservation records.
-- Apply after 012_lab_digital_notebook.sql.

CREATE UNIQUE INDEX IF NOT EXISTS lab_equipment_id_owner_unique
    ON lab_equipment (equipment_id, owner_subject);

CREATE TABLE IF NOT EXISTS lab_equipment_calibrations (
    calibration_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    equipment_id UUID NOT NULL,
    owner_subject TEXT NOT NULL,
    calibrated_on DATE NOT NULL,
    due_on DATE,
    outcome TEXT NOT NULL CHECK (outcome IN ('pass','fail','conditional')),
    performed_by TEXT NOT NULL CHECK (char_length(performed_by) BETWEEN 2 AND 160),
    certificate_reference TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (due_on IS NULL OR due_on >= calibrated_on),
    FOREIGN KEY (equipment_id, owner_subject)
        REFERENCES lab_equipment (equipment_id, owner_subject) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS lab_equipment_calibration_due_idx
    ON lab_equipment_calibrations (owner_subject, due_on, equipment_id);

CREATE TABLE IF NOT EXISTS lab_equipment_maintenance (
    maintenance_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    equipment_id UUID NOT NULL,
    owner_subject TEXT NOT NULL,
    maintenance_type TEXT NOT NULL CHECK (maintenance_type IN ('preventive','corrective','inspection','repair','other')),
    description TEXT NOT NULL CHECK (char_length(description) BETWEEN 3 AND 4000),
    performed_by TEXT NOT NULL CHECK (char_length(performed_by) BETWEEN 2 AND 160),
    performed_at TIMESTAMPTZ NOT NULL,
    next_due_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (next_due_at IS NULL OR next_due_at >= performed_at),
    FOREIGN KEY (equipment_id, owner_subject)
        REFERENCES lab_equipment (equipment_id, owner_subject) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS lab_equipment_maintenance_timeline_idx
    ON lab_equipment_maintenance (equipment_id, performed_at DESC);

CREATE TABLE IF NOT EXISTS lab_equipment_bookings (
    booking_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    equipment_id UUID NOT NULL,
    owner_subject TEXT NOT NULL,
    purpose TEXT NOT NULL CHECK (char_length(purpose) BETWEEN 3 AND 1000),
    booked_by TEXT NOT NULL CHECK (char_length(booked_by) BETWEEN 2 AND 160),
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'confirmed'
        CHECK (status IN ('confirmed','cancelled','completed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (ends_at > starts_at),
    FOREIGN KEY (equipment_id, owner_subject)
        REFERENCES lab_equipment (equipment_id, owner_subject) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS lab_equipment_booking_schedule_idx
    ON lab_equipment_bookings (equipment_id, starts_at, ends_at)
    WHERE status = 'confirmed';
CREATE INDEX IF NOT EXISTS lab_equipment_booking_owner_idx
    ON lab_equipment_bookings (owner_subject, starts_at DESC);

CREATE OR REPLACE FUNCTION prevent_equipment_record_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'equipment calibration and maintenance records are append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS lab_equipment_calibrations_no_mutation ON lab_equipment_calibrations;
CREATE TRIGGER lab_equipment_calibrations_no_mutation
    BEFORE UPDATE OR DELETE ON lab_equipment_calibrations
    FOR EACH ROW EXECUTE FUNCTION prevent_equipment_record_mutation();

DROP TRIGGER IF EXISTS lab_equipment_maintenance_no_mutation ON lab_equipment_maintenance;
CREATE TRIGGER lab_equipment_maintenance_no_mutation
    BEFORE UPDATE OR DELETE ON lab_equipment_maintenance
    FOR EACH ROW EXECUTE FUNCTION prevent_equipment_record_mutation();

COMMENT ON TABLE lab_equipment_calibrations IS
    'Append-only calibration history. A pass outcome is recorded evidence, not independent certification.';
COMMENT ON TABLE lab_equipment_maintenance IS
    'Append-only maintenance and inspection history for registered equipment.';
COMMENT ON TABLE lab_equipment_bookings IS
    'Equipment reservations; conflict checks are serialized by locking the equipment row.';
