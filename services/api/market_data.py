"""ORIOM7 public market-data ingestion V1.

Only Binance Spot public candles are connected in this milestone. No trading
permissions or exchange credentials are used. Normalised candles are persisted
to PostgreSQL when the migration has been applied.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from commercial_api import record_usage, require_api_key
from market_stream import stream_capabilities

router = APIRouter(prefix="/v1/market-data", tags=["market-data"])
BINANCE_PUBLIC_BASE = "https://data-api.binance.vision"
INTERVALS = {"1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"}


class Candle(BaseModel):
    provider: str = "binance_spot"
    symbol: str
    timeframe: str
    open_time: datetime
    close_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    quote_volume: Decimal
    trade_count: int
    is_closed: bool
    raw_sha256: str


class IngestRequest(BaseModel):
    symbol: str = Field(min_length=3, max_length=32, pattern="^[A-Za-z0-9_-]+$")
    interval: Literal["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]
    limit: int = Field(default=500, ge=1, le=1000)
    start_time: datetime | None = None
    end_time: datetime | None = None

    @classmethod
    def validate_window(cls, values):
        return values


def _utc_ms(value: datetime | None) -> int | None:
    if value is None:
        return None
    if value.tzinfo is None:
        raise ValueError("start_time and end_time must include a timezone")
    return int(value.astimezone(timezone.utc).timestamp() * 1000)


def parse_binance_klines(payload: object, symbol: str, interval: str, now: datetime | None = None) -> list[Candle]:
    if not isinstance(payload, list):
        raise ValueError("Provider response must be a list of candle arrays")
    current = now or datetime.now(timezone.utc)
    result = []
    previous_open = None
    for row in payload:
        if not isinstance(row, list) or len(row) < 11:
            raise ValueError("Provider returned a malformed kline row")
        try:
            open_ms = int(row[0])
            close_ms = int(row[6])
            open_time = datetime.fromtimestamp(open_ms / 1000, tz=timezone.utc)
            close_time = datetime.fromtimestamp(close_ms / 1000, tz=timezone.utc)
            values = [Decimal(str(row[index])) for index in (1, 2, 3, 4, 5, 7)]
            open_price, high, low, close, volume, quote_volume = values
            trade_count = int(row[8])
        except (ValueError, TypeError, InvalidOperation, OverflowError) as exc:
            raise ValueError("Provider returned invalid numeric or timestamp candle fields") from exc
        if previous_open is not None and open_time <= previous_open:
            raise ValueError("Provider candles must be strictly chronological and unique")
        if min(open_price, high, low, close) <= 0 or volume < 0 or quote_volume < 0:
            raise ValueError("Provider returned non-positive prices or negative volume")
        if high < max(open_price, low, close) or low > min(open_price, high, close):
            raise ValueError("Provider returned inconsistent OHLC values")
        if trade_count < 0 or close_time < open_time:
            raise ValueError("Provider returned invalid trade count or candle time range")
        canonical = json.dumps(row, separators=(",", ":"), ensure_ascii=True)
        result.append(Candle(
            symbol=symbol.upper(), timeframe=interval, open_time=open_time,
            close_time=close_time, open=open_price, high=high, low=low,
            close=close, volume=volume, quote_volume=quote_volume,
            trade_count=trade_count, is_closed=close_time < current,
            raw_sha256=hashlib.sha256(canonical.encode()).hexdigest(),
        ))
        previous_open = open_time
    return result


async def fetch_binance_klines(body: IngestRequest) -> list[Candle]:
    params: dict[str, object] = {"symbol": body.symbol.upper(), "interval": body.interval, "limit": body.limit}
    try:
        if body.start_time:
            params["startTime"] = _utc_ms(body.start_time)
        if body.end_time:
            params["endTime"] = _utc_ms(body.end_time)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if body.start_time and body.end_time and body.start_time > body.end_time:
        raise HTTPException(status_code=422, detail="start_time must not be after end_time")
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            response = await client.get(f"{BINANCE_PUBLIC_BASE}/api/v3/klines", params=params)
            response.raise_for_status()
            if len(response.content) > 2_000_000:
                raise HTTPException(status_code=502, detail="Market-data provider response exceeded size limit")
            payload = response.json()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status == 429 or status == 418:
            raise HTTPException(status_code=503, detail="Market-data provider rate limit or temporary ban; retry later") from exc
        raise HTTPException(status_code=502, detail=f"Market-data provider returned HTTP {status}") from exc
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail="Market-data provider is unavailable or returned invalid JSON") from exc
    try:
        return parse_binance_klines(payload, body.symbol, body.interval)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=f"Invalid provider market-data payload: {exc}") from exc


async def persist_candles(pool, candles: list[Candle]) -> int:
    if not candles:
        return 0
    sql = """
        INSERT INTO market_candles (
            provider, symbol, timeframe, open_time, close_time, open, high, low,
            close, volume, quote_volume, trade_count, is_closed, raw_sha256, fetched_at
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,NOW())
        ON CONFLICT (provider, symbol, timeframe, open_time) DO UPDATE SET
            close_time=EXCLUDED.close_time, open=EXCLUDED.open, high=EXCLUDED.high,
            low=EXCLUDED.low, close=EXCLUDED.close, volume=EXCLUDED.volume,
            quote_volume=EXCLUDED.quote_volume, trade_count=EXCLUDED.trade_count,
            is_closed=EXCLUDED.is_closed, raw_sha256=EXCLUDED.raw_sha256,
            fetched_at=NOW()
    """
    records = [
        (c.provider, c.symbol, c.timeframe, c.open_time, c.close_time, c.open,
         c.high, c.low, c.close, c.volume, c.quote_volume, c.trade_count,
         c.is_closed, c.raw_sha256)
        for c in candles
    ]
    await pool.executemany(sql, records)
    return len(records)


@router.get("/providers")
async def market_data_providers(key: dict = Depends(require_api_key)):
    return {
        "object": "oriom7_market_data_provider_catalog",
        "providers": [
            {"code": "binance_spot", "status": "connected_public_rest", "data": ["spot_klines", "exchange_instruments"], "authentication": "not_required_for_public_market_data", "documentation": "https://developers.binance.com/en/docs/products/spot/rest-api"},
            {"code": "coinbase_exchange", "status": "connected_public_rest", "data": ["exchange_instruments"], "authentication": "not_required_for_public_market_data", "documentation": "https://docs.cdp.coinbase.com/exchange/reference/exchangerestapi_getproducts"},
            {"code": "kraken_spot", "status": "connected_public_rest", "data": ["exchange_instruments"], "authentication": "not_required_for_public_market_data", "documentation": "https://docs.kraken.com/api/docs/rest-api/get-tradable-asset-pairs"},
        ],
        "notes": ["Only public spot instrument metadata is synchronised in V2; candles remain Binance-only.", "Provider-specific symbols are preserved. Cross-provider asset equivalence is not inferred.", "Check exchange data licensing and redistribution terms before commercial use."],
    }


class Instrument(BaseModel):
    provider: str
    venue: str
    instrument_id: str
    base_asset: str
    quote_asset: str
    display_symbol: str
    asset_class: str = "crypto_spot"
    status: str
    tick_size: Decimal | None = None
    lot_size: Decimal | None = None
    min_order_size: Decimal | None = None
    source_updated_at: datetime | None = None
    metadata_sha256: str


def _positive_decimal(value: object) -> Decimal | None:
    if value in (None, "", "0", 0):
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return result if result.is_finite() and result > 0 else None


def parse_binance_instruments(payload: object) -> list[Instrument]:
    if not isinstance(payload, dict) or not isinstance(payload.get("symbols"), list):
        raise ValueError("Binance exchangeInfo response is malformed")
    output = []
    for item in payload["symbols"]:
        if not isinstance(item, dict):
            continue
        filters = {f.get("filterType"): f for f in item.get("filters", []) if isinstance(f, dict)}
        price = filters.get("PRICE_FILTER", {})
        lot = filters.get("LOT_SIZE", {})
        canonical = json.dumps(item, sort_keys=True, separators=(",", ":"))
        output.append(Instrument(
            provider="binance_spot", venue="BINANCE_SPOT",
            instrument_id=str(item.get("symbol", "")),
            base_asset=str(item.get("baseAsset", "")),
            quote_asset=str(item.get("quoteAsset", "")),
            display_symbol=str(item.get("symbol", "")),
            status=str(item.get("status", "unknown")).lower(),
            tick_size=_positive_decimal(price.get("tickSize")),
            lot_size=_positive_decimal(lot.get("stepSize")),
            min_order_size=_positive_decimal(lot.get("minQty")),
            metadata_sha256=hashlib.sha256(canonical.encode()).hexdigest(),
        ))
    return _validate_instruments(output)


def parse_coinbase_instruments(payload: object) -> list[Instrument]:
    if not isinstance(payload, list):
        raise ValueError("Coinbase products response is malformed")
    output = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        canonical = json.dumps(item, sort_keys=True, separators=(",", ":"))
        product_id = str(item.get("id", ""))
        output.append(Instrument(
            provider="coinbase_exchange", venue="COINBASE_EXCHANGE",
            instrument_id=product_id,
            base_asset=str(item.get("base_currency", "")),
            quote_asset=str(item.get("quote_currency", "")),
            display_symbol=product_id,
            status=str(item.get("status", "unknown")).lower(),
            tick_size=_positive_decimal(item.get("quote_increment")),
            lot_size=_positive_decimal(item.get("base_increment")),
            min_order_size=_positive_decimal(item.get("base_min_size")),
            metadata_sha256=hashlib.sha256(canonical.encode()).hexdigest(),
        ))
    return _validate_instruments(output)


def parse_kraken_instruments(payload: object) -> list[Instrument]:
    if not isinstance(payload, dict) or payload.get("error") not in ([], None) or not isinstance(payload.get("result"), dict):
        raise ValueError("Kraken AssetPairs response is malformed or contains provider errors")
    output = []
    for pair_key, item in payload["result"].items():
        if not isinstance(item, dict):
            continue
        canonical = json.dumps(item, sort_keys=True, separators=(",", ":"))
        output.append(Instrument(
            provider="kraken_spot", venue="KRAKEN_SPOT",
            instrument_id=str(pair_key),
            base_asset=str(item.get("base", "")),
            quote_asset=str(item.get("quote", "")),
            display_symbol=str(item.get("wsname") or item.get("altname") or pair_key),
            status=str(item.get("status", "unknown")).lower(),
            tick_size=_positive_decimal(item.get("tick_size")),
            lot_size=None,
            min_order_size=_positive_decimal(item.get("ordermin")),
            metadata_sha256=hashlib.sha256(canonical.encode()).hexdigest(),
        ))
    return _validate_instruments(output)


def _validate_instruments(items: list[Instrument]) -> list[Instrument]:
    seen = set()
    for item in items:
        if not item.instrument_id or not item.base_asset or not item.quote_asset:
            raise ValueError("Provider instrument is missing its identity or base/quote asset")
        key = (item.provider, item.instrument_id)
        if key in seen:
            raise ValueError("Provider returned duplicate instrument identifiers")
        seen.add(key)
    if len(items) > 20000:
        raise ValueError("Provider instrument catalogue exceeds the 20,000 instrument safety limit")
    return items


async def fetch_instruments(provider: str) -> list[Instrument]:
    endpoints = {
        "binance_spot": ("https://data-api.binance.vision/api/v3/exchangeInfo", parse_binance_instruments),
        "coinbase_exchange": ("https://api.exchange.coinbase.com/products", parse_coinbase_instruments),
        "kraken_spot": ("https://api.kraken.com/0/public/AssetPairs", parse_kraken_instruments),
    }
    if provider not in endpoints:
        raise HTTPException(status_code=422, detail="Unsupported provider")
    url, parser = endpoints[provider]
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
            response = await client.get(url, headers={"Accept": "application/json"})
            response.raise_for_status()
            if len(response.content) > 5_000_000:
                raise HTTPException(status_code=502, detail="Instrument catalogue exceeded the 5 MB response limit")
            payload = response.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (418, 429):
            raise HTTPException(status_code=503, detail="Exchange rate limit; retry later") from exc
        raise HTTPException(status_code=502, detail=f"Exchange returned HTTP {exc.response.status_code}") from exc
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail="Exchange instrument service unavailable or invalid JSON") from exc
    try:
        return parser(payload)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=f"Invalid exchange instrument catalogue: {exc}") from exc


async def persist_instruments(pool, instruments: list[Instrument]) -> int:
    if not instruments:
        return 0
    sql = """
        INSERT INTO market_instruments (
            provider, venue, instrument_id, base_asset, quote_asset, display_symbol,
            asset_class, status, tick_size, lot_size, min_order_size,
            source_updated_at, metadata_sha256, first_seen_at, last_seen_at
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,NOW(),NOW())
        ON CONFLICT (provider, instrument_id) DO UPDATE SET
            venue=EXCLUDED.venue, base_asset=EXCLUDED.base_asset,
            quote_asset=EXCLUDED.quote_asset, display_symbol=EXCLUDED.display_symbol,
            asset_class=EXCLUDED.asset_class, status=EXCLUDED.status,
            tick_size=EXCLUDED.tick_size, lot_size=EXCLUDED.lot_size,
            min_order_size=EXCLUDED.min_order_size,
            source_updated_at=EXCLUDED.source_updated_at,
            metadata_sha256=EXCLUDED.metadata_sha256, last_seen_at=NOW()
    """
    records = [(i.provider, i.venue, i.instrument_id, i.base_asset, i.quote_asset,
                i.display_symbol, i.asset_class, i.status, i.tick_size, i.lot_size,
                i.min_order_size, i.source_updated_at, i.metadata_sha256)
               for i in instruments]
    await pool.executemany(sql, records)
    return len(records)


@router.post("/instruments/sync")
async def sync_market_instruments(provider: Literal["binance_spot", "coinbase_exchange", "kraken_spot"],
                                  request: Request, key: dict = Depends(require_api_key)):
    pool = getattr(request.app.state, "database_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="Instrument registry requires DATABASE_URL and migration 018_market_instruments.sql")
    instruments = await fetch_instruments(provider)
    try:
        stored = await persist_instruments(pool, instruments)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Instrument registry storage failed; verify migration 018 and database availability") from exc
    await record_usage(request, key, "market_instrument_sync", len(instruments), 200,
                       {"provider": provider, "stored": stored})
    return {"object": "oriom7_market_instrument_sync", "provider": provider,
            "received": len(instruments), "stored": stored,
            "identity_policy": "provider_and_instrument_id",
            "cross_provider_asset_equivalence_inferred": False}


@router.get("/instruments")
async def list_market_instruments(request: Request, provider: str | None = Query(default=None, max_length=40),
                                  status: str | None = Query(default=None, max_length=40),
                                  limit: int = Query(default=100, ge=1, le=1000),
                                  key: dict = Depends(require_api_key)):
    pool = getattr(request.app.state, "database_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="Instrument registry requires DATABASE_URL and migration 018_market_instruments.sql")
    clauses, args = [], []
    if provider:
        args.append(provider)
        clauses.append(f"provider = ${len(args)}")
    if status:
        args.append(status)
        clauses.append(f"status = ${len(args)}")
    args.append(limit)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = await pool.fetch(
        "SELECT provider, venue, instrument_id, base_asset, quote_asset, display_symbol, asset_class, status, tick_size, lot_size, min_order_size, metadata_sha256, first_seen_at, last_seen_at FROM market_instruments"
        + where + f" ORDER BY provider, instrument_id LIMIT ${len(args)}", *args)
    return {"object": "oriom7_market_instrument_list", "count": len(rows),
            "instruments": [dict(row) for row in rows],
            "identity_policy": "provider_and_instrument_id"}


@router.post("/binance/klines")
async def ingest_binance_klines(body: IngestRequest, request: Request,
                                key: dict = Depends(require_api_key)):
    pool = getattr(request.app.state, "database_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="Market-data persistence requires DATABASE_URL and migration 017_market_data.sql")
    candles = await fetch_binance_klines(body)
    try:
        stored = await persist_candles(pool, candles)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Market-data storage failed; verify migration 017 and database availability") from exc
    await record_usage(request, key, "market_data_ingestion", len(candles), 200, {
        "provider": "binance_spot", "symbol": body.symbol.upper(),
        "interval": body.interval, "stored": stored,
    })
    return {
        "object": "oriom7_market_data_ingestion",
        "provider": "binance_spot",
        "symbol": body.symbol.upper(),
        "interval": body.interval,
        "received": len(candles),
        "stored": stored,
        "closed_candles": sum(1 for candle in candles if candle.is_closed),
        "open_candles": sum(1 for candle in candles if not candle.is_closed),
        "first_open_time": candles[0].open_time.isoformat() if candles else None,
        "last_open_time": candles[-1].open_time.isoformat() if candles else None,
        "raw_response_persisted": False,
        "candles": [candle.model_dump(mode="json") for candle in candles],
        "warnings": [
            "This endpoint ingests public Binance Spot candles only; it does not connect to a trading account.",
            "The latest candle may be incomplete and is explicitly marked is_closed=false; exclude it from closed-bar research.",
            "Exchange coverage, regional availability and data redistribution rights must be reviewed for the intended use.",
        ],
    }


@router.get("/streaming/capabilities")
async def market_streaming_capabilities(key: dict = Depends(require_api_key)):
    """Describe implemented public stream adapters without implying a worker is running."""
    return stream_capabilities()
