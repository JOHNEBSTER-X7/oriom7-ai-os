"""Standalone ORIOM7 public market-data WebSocket worker.

Run: python market_stream_worker.py
Requires REDIS_URL and the optional streaming dependencies.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from collections import Counter
from typing import Any

import redis.asyncio as redis
import websockets
import httpx

from market_orderbook import OrderBook, apply_kraken_frame
from market_stream import normalise_stream_message

LOG = logging.getLogger("oriom7.market_stream")
STREAM_KEY = os.getenv("ORIOM7_MARKET_REDIS_STREAM", "oriom7:market:events")
STREAM_MAXLEN = int(os.getenv("ORIOM7_MARKET_REDIS_MAXLEN", "100000"))
QUEUE_SIZE = int(os.getenv("ORIOM7_MARKET_STREAM_QUEUE_SIZE", "5000"))
if STREAM_MAXLEN < 1 or QUEUE_SIZE < 1:
    raise RuntimeError("Redis stream retention and queue capacity must be positive integers")
METRICS = Counter()
BOOKS: dict[tuple[str, str], OrderBook] = {}


def _symbols(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


def _binance_url(symbols: list[str]) -> str:
    streams = []
    for symbol in symbols:
        s = symbol.lower()
        streams.extend([f"{s}@trade", f"{s}@bookTicker"])
    return "wss://data-stream.binance.vision/stream?streams=" + "/".join(streams)


async def _publish(redis_client: Any, queue: asyncio.Queue) -> None:
    while True:
        event = await queue.get()
        retry_delay = 1.0
        while True:
            try:
                await redis_client.xadd(
                    STREAM_KEY,
                    {"event": json.dumps(event, separators=(",", ":"), ensure_ascii=True)},
                    maxlen=STREAM_MAXLEN,
                    approximate=True,
                )
                METRICS["published"] += 1
                queue.task_done()
                break
            except asyncio.CancelledError:
                raise
            except Exception:
                METRICS["publish_errors"] += 1
                LOG.exception("Redis market event publish failed; retaining event and retrying in %.1fs", retry_delay)
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60.0)




async def _emit_book(queue: asyncio.Queue, book: OrderBook, event_type: str = "order_book") -> None:
    stats = book.analytics()
    event = {
        "schema_version": 1, "provider": book.provider,
        "venue": book.provider.upper(), "instrument_id": book.instrument_id,
        "event_type": event_type, "received_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).isoformat(),
        "exchange_time": book.last_exchange_time, "sequence": book.update_id,
        "data": stats,
    }
    try:
        queue.put_nowait(event)
        METRICS["order_books_published"] += 1
    except asyncio.QueueFull:
        METRICS["queue_dropped"] += 1


async def _run_binance_order_book(symbol: str, queue: asyncio.Queue) -> None:
    """Buffer depth deltas, bridge a REST snapshot, then enforce U/u continuity."""
    delay = 1.0
    symbol = symbol.upper()
    while True:
        connected_at = asyncio.get_running_loop().time()
        try:
            url = f"wss://data-stream.binance.vision/ws/{symbol.lower()}@depth@100ms"
            async with websockets.connect(url, ping_interval=20, ping_timeout=20,
                                          close_timeout=10, max_size=1_000_000,
                                          max_queue=2000) as socket:
                buffer = []
                async for message in socket:
                    frame = json.loads(message, parse_float=__import__("decimal").Decimal)
                    if frame.get("e") != "depthUpdate":
                        continue
                    buffer.append(frame)
                    if len(buffer) > 10000:
                        raise ConnectionError("Binance depth bootstrap buffer overflow; restarting snapshot")
                    if not buffer:
                        continue
                    async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
                        response = await client.get(
                            "https://data-api.binance.vision/api/v3/depth",
                            params={"symbol": symbol, "limit": 1000},
                        )
                        response.raise_for_status()
                        if len(response.content) > 2_000_000:
                            raise ConnectionError("Binance depth snapshot exceeded response safety limit")
                        snapshot = response.json(parse_float=__import__("decimal").Decimal)
                    book = OrderBook("binance_spot", symbol, depth=1000)
                    book.snapshot(snapshot.get("bids", []), snapshot.get("asks", []),
                                  update_id=int(snapshot["lastUpdateId"]))
                    pending = buffer
                    buffer = []
                    first_bridge = next((i for i, item in enumerate(pending)
                                         if int(item["u"]) > book.update_id
                                         and int(item["U"]) <= book.update_id + 1
                                         and int(item["u"]) >= book.update_id + 1), None)
                    if first_bridge is None:
                        raise ConnectionError("Binance snapshot could not be bridged to buffered depth events")
                    for item in pending[first_bridge:]:
                        outcome = book.apply_binance(item)
                        if outcome == "sequence_gap_resync_required":
                            raise ConnectionError("Binance depth sequence gap; book invalidated")
                    await _emit_book(queue, book, "order_book_snapshot")
                    async for message in socket:
                        frame = json.loads(message, parse_float=__import__("decimal").Decimal)
                        if frame.get("e") != "depthUpdate":
                            continue
                        outcome = book.apply_binance(frame)
                        if outcome == "sequence_gap_resync_required":
                            METRICS["binance_order_book_gaps"] += 1
                            raise ConnectionError("Binance depth sequence gap; resynchronising")
                        if outcome == "applied":
                            await _emit_book(queue, book)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            METRICS["binance_order_book_rebuilds"] += 1
            if asyncio.get_running_loop().time() - connected_at >= 60:
                delay = 1.0
            LOG.warning("Binance order book rebuild symbol=%s error=%s retry_in=%.1fs",
                        symbol, exc, delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60.0)


async def _run_provider(provider: str, url: str, symbols: list[str], queue: asyncio.Queue) -> None:
    delay = 1.0
    while True:
        connected_at = asyncio.get_running_loop().time()
        try:
            async with websockets.connect(
                url, ping_interval=20, ping_timeout=20, close_timeout=10,
                max_size=1_000_000, max_queue=1000,
            ) as socket:
                METRICS[f"{provider}_connections"] += 1
                LOG.info("Connected provider=%s symbols=%s", provider, len(symbols))
                if provider == "coinbase_exchange":
                    await socket.send(json.dumps({
                        "type": "subscribe", "product_ids": symbols,
                        "channels": ["ticker", "heartbeat", "matches", "level2_batch"],
                    }))
                elif provider == "kraken_spot":
                    await socket.send(json.dumps({
                        "method": "subscribe", "params": {
                            "channel": "trade", "symbol": symbols,
                        },
                    }))
                    await socket.send(json.dumps({
                        "method": "subscribe", "params": {
                            "channel": "ticker", "symbol": symbols,
                        },
                    }))
                async for message in socket:
                    try:
                        payload = json.loads(message, parse_float=__import__("decimal").Decimal)
                    except (TypeError, json.JSONDecodeError):
                        METRICS[f"{provider}_invalid_json"] += 1
                        continue
                    if provider == "coinbase_exchange" and payload.get("type") in ("snapshot", "l2update") and payload.get("product_id"):
                        symbol = payload["product_id"]
                        book = BOOKS.setdefault((provider, symbol), OrderBook(provider, symbol, depth=100))
                        if payload["type"] == "snapshot":
                            book.snapshot(payload.get("bids", []), payload.get("asks", []))
                            await _emit_book(queue, book, "order_book_snapshot")
                        elif book.valid:
                            book.apply_coinbase(payload.get("changes", []), payload.get("time"))
                            await _emit_book(queue, book)
                        else:
                            raise ConnectionError("Coinbase Level 2 update received before snapshot")
                        continue
                    if provider == "kraken_spot" and payload.get("channel") == "book":
                        for item in payload.get("data", []):
                            symbol = item.get("symbol", "unknown")
                            book = BOOKS.setdefault((provider, symbol), OrderBook(provider, symbol, depth=25))
                            if not apply_kraken_frame(book, payload):
                                METRICS["kraken_order_book_checksum_failures"] += 1
                                raise ConnectionError(f"Kraken order book checksum failed for {symbol}")
                            await _emit_book(queue, book, "order_book_snapshot" if payload.get("type") == "snapshot" else "order_book")
                        continue
                    for event in normalise_stream_message(provider, payload):
                        # Trade/ticker channels are not a complete order-book delta
                        # sequence. Do not infer packet loss from their IDs. The tested
                        # tracker is reserved for sequence-guaranteed book-delta adapters.
                        event.update({"sequence_checked": False, "sequence_gap": False,
                                      "previous_sequence": None})
                        try:
                            queue.put_nowait(event)
                            METRICS["queued"] += 1
                        except asyncio.QueueFull:
                            METRICS["queue_dropped"] += 1
                raise ConnectionError("WebSocket connection closed by provider")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            METRICS[f"{provider}_disconnects"] += 1
            if asyncio.get_running_loop().time() - connected_at >= 60:
                delay = 1.0
            LOG.warning("Provider disconnected provider=%s error=%s retry_in=%.1fs", provider, exc, delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60.0)


async def _report_metrics(queue: asyncio.Queue) -> None:
    while True:
        await asyncio.sleep(60)
        LOG.info("stream_metrics queue_depth=%s queue_capacity=%s counters=%s",
                 queue.qsize(), QUEUE_SIZE, dict(METRICS))


async def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        raise RuntimeError("REDIS_URL is required; streaming events are not silently discarded.")
    binance_symbols = _symbols("ORIOM7_BINANCE_STREAM_SYMBOLS", "BTCUSDT")
    coinbase_symbols = _symbols("ORIOM7_COINBASE_STREAM_PRODUCTS", "BTC-USD")
    kraken_symbols = _symbols("ORIOM7_KRAKEN_STREAM_SYMBOLS", "BTC/USD")
    if len(binance_symbols) > 512:
        raise RuntimeError("Binance supports at most 512 configured symbols in this combined-stream worker")
    if len(coinbase_symbols) > 5:
        raise RuntimeError("Coinbase subscription plan: limit this worker to 5 products across four channels; reduce configured products")
    if not kraken_symbols:
        raise RuntimeError("Configure at least one Kraken symbol")
    queue: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_SIZE)
    client = redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=5,
                            socket_timeout=5, health_check_interval=30)
    await client.ping()
    tasks = [
        asyncio.create_task(_publish(client, queue), name="redis-publisher"),
        asyncio.create_task(_report_metrics(queue), name="metrics-reporter"),
        *[asyncio.create_task(_run_binance_order_book(symbol, queue), name=f"binance-l2-{symbol}") for symbol in binance_symbols],
        asyncio.create_task(_run_provider("binance_spot", _binance_url(binance_symbols), binance_symbols, queue)),
        asyncio.create_task(_run_provider("coinbase_exchange", "wss://ws-feed.exchange.coinbase.com",
                                          coinbase_symbols, queue)),
        asyncio.create_task(_run_provider("kraken_spot", "wss://ws.kraken.com/v2",
                                          kraken_symbols, queue)),
    ]
    try:
        await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
