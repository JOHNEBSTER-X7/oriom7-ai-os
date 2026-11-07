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
            {"code": "binance_spot", "status": "connected_public_rest", "data": ["spot_klines", "exchange_symbols"], "authentication": "not_required_for_public_market_data", "documentation": "https://developers.binance.com/en/docs/products/spot/rest-api"},
            {"code": "coinbase_exchange", "status": "planned", "data": ["candles", "products"], "authentication": "public_endpoints"},
            {"code": "kraken_spot", "status": "planned", "data": ["ohlc", "asset_pairs"], "authentication": "public_endpoints"},
        ],
        "notes": ["Provider availability and instrument coverage vary by jurisdiction and product.", "Check exchange data licensing and redistribution terms before commercial use."],
    }


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
