"""Canonical public market-data stream event parsing and sequence diagnostics."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        # Binance event/trade times are epoch milliseconds.
        return datetime.fromtimestamp(float(value) / 1000, tz=timezone.utc).isoformat()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
        except ValueError:
            return None
    return None


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def normalise_stream_message(provider: str, payload: Any, received_at: datetime | None = None) -> list[dict[str, Any]]:
    """Convert a public venue message into zero or more canonical events."""
    now = (received_at or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    events: list[dict[str, Any]] = []
    if provider == "binance_spot":
        if not isinstance(payload, dict):
            return events
        raw = payload.get("data", payload)
        if not isinstance(raw, dict):
            return events
        kind = raw.get("e")
        if kind == "trade":
            data = {
                "price": raw.get("p"), "quantity": raw.get("q"),
                "trade_id": raw.get("t"),
                "aggressor_side": "sell" if raw.get("m") is True else "buy",
            }
            events.append(_event(provider, raw.get("s"), "trade", raw.get("T") or raw.get("E"), raw.get("t"), data, raw, now))
        elif kind == "bookTicker" or all(k in raw for k in ("b", "B", "a", "A", "s")):
            data = {"best_bid": raw.get("b"), "best_bid_size": raw.get("B"),
                    "best_ask": raw.get("a"), "best_ask_size": raw.get("A")}
            events.append(_event(provider, raw.get("s"), "ticker", raw.get("E"), raw.get("u"), data, raw, now))
    elif provider == "coinbase_exchange":
        if not isinstance(payload, dict):
            return events
        kind = payload.get("type")
        symbol = payload.get("product_id")
        sequence = payload.get("sequence")
        if kind == "ticker":
            data = {"price": payload.get("price"), "last_size": payload.get("last_size"),
                    "best_bid": payload.get("best_bid"), "best_ask": payload.get("best_ask"),
                    "side": payload.get("side"), "trade_id": payload.get("trade_id")}
            events.append(_event(provider, symbol, "ticker", payload.get("time"), sequence, data, payload, now))
        elif kind == "heartbeat":
            data = {"last_trade_id": payload.get("last_trade_id")}
            events.append(_event(provider, symbol, "heartbeat", payload.get("time"), sequence, data, payload, now))
        elif kind == "match":
            data = {"price": payload.get("price"), "quantity": payload.get("size"),
                    "side": payload.get("side"), "trade_id": payload.get("trade_id")}
            events.append(_event(provider, symbol, "trade", payload.get("time"), sequence, data, payload, now))
    elif provider == "kraken_spot":
        if not isinstance(payload, dict):
            return events
        channel = payload.get("channel")
        rows = payload.get("data")
        if channel == "heartbeat":
            events.append(_event(provider, "venue", "heartbeat", None, None, {}, payload, now))
        elif isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                symbol = row.get("symbol")
                if channel == "trade":
                    data = {"price": row.get("price"), "quantity": row.get("qty"),
                            "side": row.get("side"), "trade_id": row.get("trade_id")}
                    events.append(_event(provider, symbol, "trade", row.get("timestamp"), row.get("trade_id"), data, row, now))
                elif channel == "ticker":
                    data = {"last": row.get("last"), "bid": row.get("bid"),
                            "ask": row.get("ask"), "volume": row.get("volume")}
                    events.append(_event(provider, symbol, "ticker", row.get("timestamp"), payload.get("sequence"), data, row, now))
    return events


def _event(provider: str, symbol: Any, kind: str, timestamp: Any, sequence: Any,
           data: dict[str, Any], raw: Any, received_at: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "provider": provider,
        "venue": provider.upper(),
        "instrument_id": str(symbol or "unknown"),
        "event_type": kind,
        "exchange_time": _iso(timestamp),
        "received_at": received_at,
        "sequence": sequence,
        "data": data,
        "raw_sha256": _hash(raw),
    }


class SequenceGapTracker:
    """Detect discontinuities only for feeds exposing a monotonic sequence."""
    def __init__(self) -> None:
        self._last: dict[tuple[str, str], int] = {}

    def observe(self, provider: str, instrument_id: str, sequence: Any) -> dict[str, Any]:
        if not isinstance(sequence, int) or isinstance(sequence, bool):
            return {"sequence_checked": False, "sequence_gap": False, "previous_sequence": None}
        key = (provider, instrument_id)
        previous = self._last.get(key)
        gap = previous is not None and sequence != previous + 1
        self._last[key] = sequence
        return {"sequence_checked": previous is not None, "sequence_gap": gap,
                "previous_sequence": previous}


def stream_capabilities() -> dict[str, Any]:
    return {
        "status": "worker_optional_not_started_by_api",
        "providers": [
            {"code": "binance_spot", "status": "adapter_implemented", "channels": ["trade", "bookTicker", "depth@100ms"], "book_integrity": "REST snapshot plus U/u update continuity", "endpoint": "wss://data-stream.binance.vision"},
            {"code": "coinbase_exchange", "status": "adapter_implemented", "channels": ["ticker", "heartbeat", "match", "level2_batch"], "book_integrity": "Level 2 snapshot and guaranteed-delivery channel", "endpoint": "wss://ws-feed.exchange.coinbase.com"},
            {"code": "kraken_spot", "status": "adapter_implemented", "channels": ["trade", "ticker", "heartbeat", "book"], "book_integrity": "CRC32 top-10 checksum", "endpoint": "wss://ws.kraken.com/v2"},
        ],
        "sink": "Redis Streams",
        "limitations": ["Level 2 books are maintained in the optional worker and published as Redis events; the API does not host an in-memory shared book service.",
                        "Binance snapshot bridging and sequence continuity, Coinbase Level 2 snapshots/updates, and Kraken CRC32 verification are implemented in the worker.",
                        "Analytics are indicative and exclude hidden liquidity, latency, fees, queue priority and market impact beyond visible levels.",
                        "This API catalogue does not assert that a separate streaming worker is running."],
    }
