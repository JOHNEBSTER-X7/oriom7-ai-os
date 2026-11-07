-- ORIOM7 organisation invitations and membership administration.
CREATE TABLE IF NOT EXISTS oriom7_organisation_invitations (
 invitation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 organisation_id UUID NOT NULL REFERENCES oriom7_organisations(organisation_id) ON DELETE CASCADE,
 email TEXT NOT NULL,
 role TEXT NOT NULL CHECK(role IN ('admin','developer','billing_viewer')),
 token_hash TEXT NOT NULL UNIQUE,
 invited_by_subject TEXT NOT NULL,
 expires_at TIMESTAMPTZ NOT NULL,
 accepted_subject TEXT,
 accepted_at TIMESTAMPTZ,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS oriom7_org_invites_email_idx
 ON oriom7_organisation_invitations(lower(email),expires_at DESC)
 WHERE accepted_at IS NULL;
