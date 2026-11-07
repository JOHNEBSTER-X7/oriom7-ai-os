-- ORIOM7 normalised public market candles. Migration 017.
CREATE TABLE IF NOT EXISTS market_candles (
    provider TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    open_time TIMESTAMPTZ NOT NULL,
    close_time TIMESTAMPTZ NOT NULL,
    open NUMERIC(38, 18) NOT NULL CHECK (open > 0),
    high NUMERIC(38, 18) NOT NULL CHECK (high > 0),
    low NUMERIC(38, 18) NOT NULL CHECK (low > 0),
    close NUMERIC(38, 18) NOT NULL CHECK (close > 0),
    volume NUMERIC(38, 18) NOT NULL CHECK (volume >= 0),
    quote_volume NUMERIC(38, 18) NOT NULL CHECK (quote_volume >= 0),
    trade_count BIGINT NOT NULL CHECK (trade_count >= 0),
    is_closed BOOLEAN NOT NULL DEFAULT FALSE,
    raw_sha256 CHAR(64) NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (provider, symbol, timeframe, open_time),
    CHECK (high >= GREATEST(open, low, close)),
    CHECK (low <= LEAST(open, high, close)),
    CHECK (close_time >= open_time)
);
CREATE INDEX IF NOT EXISTS market_candles_symbol_time_idx
    ON market_candles (symbol, timeframe, open_time DESC);
CREATE INDEX IF NOT EXISTS market_candles_provider_fetched_idx
    ON market_candles (provider, fetched_at DESC);
