-- ORIOM7 identity, organisation and billing-readiness foundation.
-- This migration does not create payment credentials or activate paid subscriptions.

CREATE TABLE IF NOT EXISTS oriom7_accounts (
    account_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_id TEXT NOT NULL UNIQUE,
    display_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS oriom7_organisations (
    organisation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL CHECK (char_length(name) BETWEEN 2 AND 120),
    slug TEXT NOT NULL UNIQUE CHECK (slug ~ '^[a-z0-9][a-z0-9-]{1,58}[a-z0-9]$'),
    created_by_subject TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS oriom7_organisation_members (
    organisation_id UUID NOT NULL REFERENCES oriom7_organisations(organisation_id) ON DELETE CASCADE,
    subject_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('owner','admin','developer','billing_viewer')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (organisation_id, subject_id)
);
CREATE INDEX IF NOT EXISTS oriom7_org_members_subject_idx ON oriom7_organisation_members(subject_id, created_at DESC);

CREATE TABLE IF NOT EXISTS oriom7_plan_catalog (
    plan_code TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    description TEXT NOT NULL,
    monthly_price_minor BIGINT,
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    monthly_request_limit BIGINT,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (monthly_price_minor IS NULL OR monthly_price_minor >= 0),
    CHECK (monthly_request_limit IS NULL OR monthly_request_limit >= 0)
);

INSERT INTO oriom7_plan_catalog(plan_code,display_name,description,monthly_price_minor,currency,monthly_request_limit)
VALUES
 ('starter','Starter','Development access; no paid entitlement is implied.',0,'USD',1000),
 ('builder','Builder','For individual application development; commercial pricing pending.',NULL,'USD',25000),
 ('business','Business','For production teams; commercial pricing pending.',NULL,'USD',250000),
 ('enterprise','Enterprise','Custom deployment and commercial terms; contact required.',NULL,'USD',NULL)
ON CONFLICT (plan_code) DO NOTHING;

CREATE TABLE IF NOT EXISTS oriom7_subscriptions (
    subscription_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES oriom7_accounts(account_id),
    organisation_id UUID REFERENCES oriom7_organisations(organisation_id),
    plan_code TEXT NOT NULL REFERENCES oriom7_plan_catalog(plan_code),
    provider TEXT NOT NULL DEFAULT 'unconfigured',
    provider_subscription_id TEXT,
    status TEXT NOT NULL DEFAULT 'not_configured'
      CHECK (status IN ('not_configured','pending','trialing','active','past_due','canceled','incomplete')),
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS oriom7_subscriptions_account_idx ON oriom7_subscriptions(account_id, created_at DESC);

CREATE TABLE IF NOT EXISTS oriom7_invoices (
    invoice_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES oriom7_accounts(account_id),
    subscription_id UUID REFERENCES oriom7_subscriptions(subscription_id),
    provider TEXT NOT NULL,
    provider_invoice_id TEXT,
    invoice_number TEXT,
    currency CHAR(3) NOT NULL,
    amount_due_minor BIGINT NOT NULL CHECK (amount_due_minor >= 0),
    amount_paid_minor BIGINT NOT NULL DEFAULT 0 CHECK (amount_paid_minor >= 0),
    status TEXT NOT NULL CHECK (status IN ('draft','open','paid','void','uncollectible')),
    hosted_invoice_url TEXT,
    issued_at TIMESTAMPTZ,
    due_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(provider, provider_invoice_id)
);
CREATE INDEX IF NOT EXISTS oriom7_invoices_account_idx ON oriom7_invoices(account_id, created_at DESC);

CREATE TABLE IF NOT EXISTS oriom7_payment_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL,
    provider_event_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    processed_at TIMESTAMPTZ,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(provider, provider_event_id)
);

CREATE TABLE IF NOT EXISTS oriom7_usage_ledger (
    usage_id BIGSERIAL PRIMARY KEY,
    account_id UUID NOT NULL REFERENCES oriom7_accounts(account_id),
    organisation_id UUID REFERENCES oriom7_organisations(organisation_id),
    api_key_id UUID REFERENCES developer_api_keys(api_key_id),
    product_code TEXT NOT NULL,
    quantity BIGINT NOT NULL CHECK (quantity >= 0),
    idempotency_key TEXT UNIQUE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS oriom7_usage_account_date_idx ON oriom7_usage_ledger(account_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS oriom7_usage_org_date_idx ON oriom7_usage_ledger(organisation_id, occurred_at DESC);
