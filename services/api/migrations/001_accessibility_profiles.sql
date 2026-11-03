-- ORIOM7 user-selected accessibility preferences.
-- The subject_id must be an opaque identifier issued by trusted authentication.
-- Never store diagnostic labels or inferred health information in this table.
CREATE TABLE IF NOT EXISTS accessibility_profiles (
    subject_id TEXT PRIMARY KEY,
    profile JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT accessibility_profile_is_object CHECK (jsonb_typeof(profile) = 'object')
);

CREATE INDEX IF NOT EXISTS accessibility_profiles_updated_at_idx
    ON accessibility_profiles (updated_at);
