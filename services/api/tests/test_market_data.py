from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import market_data
import commercial_api
from fastapi import FastAPI
from fastapi.testclient import TestClient


def kline(open_ms, close_ms, close="101"):
    return [open_ms, "100", "102", "99", close, "10", close_ms,
            "1000", 12, "5", "500", "0"]


def test_parser_normalises_and_marks_open_candle():
    now = datetime(2025, 1, 1, 0, 1, 30, tzinfo=timezone.utc)
    rows = [kline(1735689600000, 1735689659999), kline(1735689660000, 1735689719999)]
    candles = market_data.parse_binance_klines(rows, "btcusdt", "1m", now)
    assert candles[0].symbol == "BTCUSDT"
    assert candles[0].is_closed is True
    assert candles[1].is_closed is False
    assert candles[0].raw_sha256 != candles[1].raw_sha256


def test_parser_rejects_duplicate_or_unordered_open_times():
    rows = [kline(1735689600000, 1735689659999), kline(1735689600000, 1735689659999)]
    try:
        market_data.parse_binance_klines(rows, "BTCUSDT", "1m")
        assert False, "duplicate timestamps must fail"
    except ValueError as exc:
        assert "chronological" in str(exc)


def test_parser_rejects_inconsistent_ohlc():
    row = kline(1735689600000, 1735689659999)
    row[2] = "98"
    try:
        market_data.parse_binance_klines([row], "BTCUSDT", "1m")
        assert False, "inconsistent OHLC must fail"
    except ValueError as exc:
        assert "inconsistent" in str(exc)


def test_ingestion_requires_database_persistence(monkeypatch):
    app = FastAPI()
    app.include_router(market_data.router)
    app.state.database_pool = None
    app.dependency_overrides[commercial_api.require_api_key] = lambda: {"owner_id": "acct"}
    monkeypatch.setattr(market_data, "fetch_binance_klines", AsyncMock(return_value=[]))
    response = TestClient(app).post("/v1/market-data/binance/klines", json={
        "symbol": "BTCUSDT", "interval": "1m", "limit": 10,
    })
    assert response.status_code == 503
    assert "migration 017" in response.json()["detail"]


def test_ingestion_persists_and_meters_usage(monkeypatch):
    class Pool:
        async def executemany(self, sql, records):
            self.sql = sql
            self.records = records
    pool = Pool()
    app = FastAPI()
    app.include_router(market_data.router)
    app.state.database_pool = pool
    app.dependency_overrides[commercial_api.require_api_key] = lambda: {"owner_id": "acct"}
    candles = market_data.parse_binance_klines(
        [kline(1735689600000, 1735689659999)],
        "BTCUSDT", "1m", datetime(2025, 1, 2, tzinfo=timezone.utc)
    )
    monkeypatch.setattr(market_data, "fetch_binance_klines", AsyncMock(return_value=candles))
    usage = AsyncMock()
    monkeypatch.setattr(market_data, "record_usage", usage)
    response = TestClient(app).post("/v1/market-data/binance/klines", json={
        "symbol": "BTCUSDT", "interval": "1m", "limit": 10,
    })
    assert response.status_code == 200
    assert response.json()["stored"] == 1
    assert len(pool.records) == 1
    usage.assert_awaited_once()
    assert usage.await_args.args[2] == "market_data_ingestion"


def test_request_rejects_invalid_interval():
    try:
        market_data.IngestRequest(symbol="BTCUSDT", interval="2m")
        assert False, "unsupported interval must fail"
    except ValueError:
        pass


def test_coinbase_instrument_normalisation_preserves_provider_symbol():
    result = market_data.parse_coinbase_instruments([{
        "id": "BTC-USD", "base_currency": "BTC", "quote_currency": "USD",
        "quote_increment": "0.01", "base_increment": "0.00000001",
        "base_min_size": "0.0001", "status": "online",
    }])
    assert len(result) == 1
    assert result[0].provider == "coinbase_exchange"
    assert result[0].instrument_id == "BTC-USD"
    assert result[0].tick_size == market_data.Decimal("0.01")


def test_kraken_instrument_normalisation_preserves_internal_and_display_symbols():
    result = market_data.parse_kraken_instruments({"error": [], "result": {
        "XXBTZUSD": {"altname": "XBTUSD", "wsname": "XBT/USD",
                     "base": "XXBT", "quote": "ZUSD", "status": "online",
                     "tick_size": "0.1", "ordermin": "0.0001"}
    }})
    assert result[0].instrument_id == "XXBTZUSD"
    assert result[0].display_symbol == "XBT/USD"
    assert result[0].base_asset == "XXBT"
    assert result[0].quote_asset == "ZUSD"


def test_binance_instrument_normalisation_reads_filters():
    result = market_data.parse_binance_instruments({"symbols": [{
        "symbol": "BTCUSDT", "baseAsset": "BTC", "quoteAsset": "USDT",
        "status": "TRADING", "filters": [
            {"filterType": "PRICE_FILTER", "tickSize": "0.01"},
            {"filterType": "LOT_SIZE", "stepSize": "0.00001", "minQty": "0.0001"}
        ]
    }]})
    assert result[0].tick_size == market_data.Decimal("0.01")
    assert result[0].lot_size == market_data.Decimal("0.00001")
    assert result[0].status == "trading"


def test_instrument_registry_sync_requires_migration_018(monkeypatch):
    app = FastAPI()
    app.include_router(market_data.router)
    app.state.database_pool = None
    app.dependency_overrides[commercial_api.require_api_key] = lambda: {"owner_id": "acct"}
    monkeypatch.setattr(market_data, "fetch_instruments", AsyncMock(return_value=[]))
    response = TestClient(app).post("/v1/market-data/instruments/sync?provider=coinbase_exchange")
    assert response.status_code == 503
    assert "migration 018" in response.json()["detail"]


def test_instrument_registry_sync_persists_and_meters(monkeypatch):
    class Pool:
        async def executemany(self, sql, records):
            self.sql = sql
            self.records = records
    pool = Pool()
    app = FastAPI()
    app.include_router(market_data.router)
    app.state.database_pool = pool
    app.dependency_overrides[commercial_api.require_api_key] = lambda: {"owner_id": "acct"}
    instruments = market_data.parse_coinbase_instruments([{
        "id": "BTC-USD", "base_currency": "BTC", "quote_currency": "USD",
        "status": "online"
    }])
    monkeypatch.setattr(market_data, "fetch_instruments", AsyncMock(return_value=instruments))
    usage = AsyncMock()
    monkeypatch.setattr(market_data, "record_usage", usage)
    response = TestClient(app).post("/v1/market-data/instruments/sync?provider=coinbase_exchange")
    assert response.status_code == 200
    assert response.json()["stored"] == 1
    assert len(pool.records) == 1
    assert pool.records[0][0] == "coinbase_exchange"
    usage.assert_awaited_once()
