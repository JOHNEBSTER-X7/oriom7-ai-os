-- Commercial developer API foundation: hashed API keys and auditable usage.
CREATE TABLE IF NOT EXISTS developer_api_keys (
    api_key_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id TEXT NOT NULL,
    name TEXT NOT NULL CHECK (char_length(name) BETWEEN 1 AND 80),
    key_prefix TEXT NOT NULL,
    key_hash TEXT NOT NULL UNIQUE,
    plan_code TEXT NOT NULL DEFAULT 'starter',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS developer_api_keys_owner_idx
    ON developer_api_keys (owner_id, created_at DESC);

CREATE TABLE IF NOT EXISTS developer_api_usage (
    usage_id BIGSERIAL PRIMARY KEY,
    api_key_id UUID NOT NULL REFERENCES developer_api_keys(api_key_id),
    product_code TEXT NOT NULL,
    request_id UUID NOT NULL DEFAULT gen_random_uuid(),
    units BIGINT NOT NULL DEFAULT 1 CHECK (units >= 0),
    status_code INTEGER NOT NULL,
    estimated_cost_usd NUMERIC(14, 8),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS developer_api_usage_key_date_idx
    ON developer_api_usage (api_key_id, created_at DESC);
CREATE INDEX IF NOT EXISTS developer_api_usage_product_date_idx
    ON developer_api_usage (product_code, created_at DESC);
