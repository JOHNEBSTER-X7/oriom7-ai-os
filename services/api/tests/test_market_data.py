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


from market_stream import SequenceGapTracker, normalise_stream_message


def test_binance_trade_stream_normalises_to_canonical_event():
    events = normalise_stream_message("binance_spot", {
        "stream": "btcusdt@trade",
        "data": {"e": "trade", "E": 1735689600123, "T": 1735689600000,
                 "s": "BTCUSDT", "t": 99, "p": "42000.10", "q": "0.2", "m": True}
    })
    assert len(events) == 1
    event = events[0]
    assert event["provider"] == "binance_spot"
    assert event["instrument_id"] == "BTCUSDT"
    assert event["event_type"] == "trade"
    assert event["data"]["aggressor_side"] == "sell"
    assert event["data"]["price"] == "42000.10"
    assert len(event["raw_sha256"]) == 64


def test_coinbase_ticker_stream_normalises_product_and_sequence():
    events = normalise_stream_message("coinbase_exchange", {
        "type": "ticker", "product_id": "BTC-USD", "sequence": 123,
        "time": "2026-11-07T10:00:00Z", "price": "50000",
        "best_bid": "49999", "best_ask": "50001", "last_size": "0.01"
    })
    assert len(events) == 1
    assert events[0]["instrument_id"] == "BTC-USD"
    assert events[0]["sequence"] == 123
    assert events[0]["data"]["best_ask"] == "50001"


def test_kraken_trade_stream_expands_batch_into_events():
    events = normalise_stream_message("kraken_spot", {
        "channel": "trade", "type": "update", "data": [
            {"symbol": "BTC/USD", "price": 50000, "qty": 0.1,
             "side": "buy", "trade_id": 42, "timestamp": "2026-11-07T10:00:00.123Z"},
            {"symbol": "ETH/USD", "price": 2000, "qty": 1,
             "side": "sell", "trade_id": 43, "timestamp": "2026-11-07T10:00:01.123Z"}
        ]
    })
    assert len(events) == 2
    assert events[0]["instrument_id"] == "BTC/USD"
    assert events[1]["data"]["side"] == "sell"


def test_sequence_tracker_reports_gap_and_isolates_instruments():
    tracker = SequenceGapTracker()
    assert tracker.observe("coinbase_exchange", "BTC-USD", 10)["sequence_checked"] is False
    assert tracker.observe("coinbase_exchange", "BTC-USD", 11)["sequence_gap"] is False
    gap = tracker.observe("coinbase_exchange", "BTC-USD", 13)
    assert gap["sequence_gap"] is True
    assert gap["previous_sequence"] == 11
    assert tracker.observe("coinbase_exchange", "ETH-USD", 500)["sequence_gap"] is False


def test_stream_capabilities_are_explicit_about_worker_state():
    result = market_stream.stream_capabilities()
    assert result["status"] == "worker_optional_not_started_by_api"
    assert all(provider["status"] == "adapter_implemented" for provider in result["providers"])
    assert any("order-book" in item for item in result["limitations"])


def test_streaming_capabilities_endpoint_is_authenticated_and_truthful():
    app = FastAPI()
    app.include_router(market_data.router)
    app.dependency_overrides[commercial_api.require_api_key] = lambda: {"owner_id": "acct"}
    response = TestClient(app).get("/v1/market-data/streaming/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "worker_optional_not_started_by_api"
    assert body["sink"] == "Redis Streams"
    assert len(body["providers"]) == 3
