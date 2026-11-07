-- ORIOM7 global provider-specific instrument master. Migration 018.
CREATE TABLE IF NOT EXISTS market_instruments (
    provider TEXT NOT NULL,
    venue TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    base_asset TEXT NOT NULL,
    quote_asset TEXT NOT NULL,
    display_symbol TEXT NOT NULL,
    asset_class TEXT NOT NULL DEFAULT 'crypto_spot',
    status TEXT NOT NULL,
    tick_size NUMERIC(38, 18),
    lot_size NUMERIC(38, 18),
    min_order_size NUMERIC(38, 18),
    source_updated_at TIMESTAMPTZ,
    metadata_sha256 CHAR(64) NOT NULL,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (provider, instrument_id),
    CHECK (length(provider) > 0),
    CHECK (length(instrument_id) > 0),
    CHECK (length(base_asset) > 0),
    CHECK (length(quote_asset) > 0),
    CHECK (tick_size IS NULL OR tick_size > 0),
    CHECK (lot_size IS NULL OR lot_size > 0),
    CHECK (min_order_size IS NULL OR min_order_size > 0)
);
CREATE INDEX IF NOT EXISTS market_instruments_assets_idx
    ON market_instruments (base_asset, quote_asset, provider);
CREATE INDEX IF NOT EXISTS market_instruments_status_idx
    ON market_instruments (provider, status, instrument_id);
CREATE INDEX IF NOT EXISTS market_instruments_seen_idx
    ON market_instruments (last_seen_at DESC);
