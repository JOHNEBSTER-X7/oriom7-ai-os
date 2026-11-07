"""Validated provider-specific Level 2 order-book reconstruction and analytics.

All price/quantity arithmetic uses Decimal. Books are invalidated on sequence
or checksum failure; consumers must resynchronise before trusting analytics.
"""
from __future__ import annotations

import zlib
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any


def dec(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("Invalid order-book price or quantity") from exc
    if not result.is_finite() or result <= 0:
        raise ValueError("Order-book price and quantity must be finite and positive")
    return result


@dataclass
class OrderBook:
    provider: str
    instrument_id: str
    depth: int = 25
    bids: dict[Decimal, Decimal] = field(default_factory=dict)
    asks: dict[Decimal, Decimal] = field(default_factory=dict)
    update_id: int | None = None
    valid: bool = False
    checksum: int | None = None
    last_exchange_time: str | None = None

    def __post_init__(self) -> None:
        if self.depth < 1 or self.depth > 1000:
            raise ValueError("Book depth must be between 1 and 1000")

    def _levels(self, values: list[Any]) -> dict[Decimal, Decimal]:
        result: dict[Decimal, Decimal] = {}
        for row in values:
            if isinstance(row, dict):
                price, qty = row.get("price"), row.get("qty")
            elif isinstance(row, (list, tuple)) and len(row) >= 2:
                price, qty = row[0], row[1]
            else:
                raise ValueError("Malformed price level")
            p = dec(price)
            try:
                q = Decimal(str(qty))
            except (InvalidOperation, ValueError, TypeError) as exc:
                raise ValueError("Invalid order-book quantity") from exc
            if not q.is_finite() or q < 0:
                raise ValueError("Order-book quantity must be finite and non-negative")
            if q > 0:
                result[p] = q
        return result

    def snapshot(self, bids: list[Any], asks: list[Any], update_id: int | None = None,
                 exchange_time: str | None = None) -> None:
        self.bids = self._levels(bids)
        self.asks = self._levels(asks)
        self.update_id = update_id
        self.last_exchange_time = exchange_time
        self._trim()
        self.valid = True

    def _trim(self) -> None:
        self.bids = dict(sorted(self.bids.items(), reverse=True)[:self.depth])
        self.asks = dict(sorted(self.asks.items())[:self.depth])

    def _apply_levels(self, side: dict[Decimal, Decimal], changes: list[Any]) -> None:
        for row in changes:
            if isinstance(row, dict):
                price, qty = row.get("price"), row.get("qty")
            elif isinstance(row, (list, tuple)) and len(row) >= 2:
                price, qty = row[0], row[1]
            else:
                raise ValueError("Malformed order-book delta")
            p = dec(price)
            try:
                q = Decimal(str(qty))
            except (InvalidOperation, ValueError, TypeError) as exc:
                raise ValueError("Invalid order-book delta quantity") from exc
            if not q.is_finite() or q < 0:
                raise ValueError("Order-book delta quantity must be non-negative")
            if q == 0:
                side.pop(p, None)
            else:
                side[p] = q

    def apply_absolute(self, bids: list[Any], asks: list[Any],
                       exchange_time: str | None = None) -> None:
        if not self.valid:
            raise RuntimeError("Cannot apply order-book update before a snapshot")
        self._apply_levels(self.bids, bids)
        self._apply_levels(self.asks, asks)
        self._trim()
        self.last_exchange_time = exchange_time

    def apply_binance(self, event: dict[str, Any]) -> str:
        if not self.valid or self.update_id is None:
            raise RuntimeError("Binance book requires a REST snapshot before depth updates")
        first, final = int(event["U"]), int(event["u"])
        if final <= self.update_id:
            return "stale_ignored"
        if first > self.update_id + 1:
            self.valid = False
            return "sequence_gap_resync_required"
        if not (first <= self.update_id + 1 <= final):
            self.valid = False
            return "sequence_gap_resync_required"
        self._apply_levels(self.bids, event.get("b", []))
        self._apply_levels(self.asks, event.get("a", []))
        self.update_id = final
        self._trim()
        self.last_exchange_time = str(event.get("E")) if event.get("E") is not None else None
        return "applied"

    def apply_coinbase(self, changes: list[list[Any]], exchange_time: str | None = None) -> None:
        if not self.valid:
            raise RuntimeError("Coinbase Level 2 book requires a snapshot")
        for change in changes:
            if not isinstance(change, (list, tuple)) or len(change) != 3:
                raise ValueError("Malformed Coinbase Level 2 change")
            side, price, size = change
            if side == "buy":
                self._apply_levels(self.bids, [[price, size]])
            elif side == "sell":
                self._apply_levels(self.asks, [[price, size]])
            else:
                raise ValueError("Unknown Coinbase Level 2 side")
        self._trim()
        self.last_exchange_time = exchange_time

    def apply_kraken(self, bids: list[Any], asks: list[Any], checksum: int,
                     exchange_time: str | None = None) -> bool:
        if not self.valid:
            raise RuntimeError("Kraken book requires a snapshot")
        self._apply_levels(self.bids, bids)
        self._apply_levels(self.asks, asks)
        self._trim()
        self.last_exchange_time = exchange_time
        self.checksum = int(checksum)
        if kraken_checksum(self.bids, self.asks) != self.checksum:
            self.valid = False
            return False
        return True

    def top_levels(self, limit: int = 25) -> dict[str, list[list[str]]]:
        if not self.valid:
            raise RuntimeError("Order book is invalid; resynchronise before reading levels")
        if limit < 1 or limit > self.depth:
            raise ValueError("Requested levels must be between 1 and configured book depth")
        return {
            "bids": [[str(price), str(qty)] for price, qty in sorted(self.bids.items(), reverse=True)[:limit]],
            "asks": [[str(price), str(qty)] for price, qty in sorted(self.asks.items())[:limit]],
        }

    def analytics(self) -> dict[str, Any]:
        if not self.valid:
            raise RuntimeError("Order book is invalid; resynchronise before analytics")
        bids = sorted(self.bids.items(), reverse=True)
        asks = sorted(self.asks.items())
        if not bids or not asks:
            raise ValueError("Both bid and ask sides are required for analytics")
        best_bid, bid_qty = bids[0]
        best_ask, ask_qty = asks[0]
        if best_bid >= best_ask:
            raise ValueError("Crossed or locked book rejected")
        mid = (best_bid + best_ask) / 2
        spread = best_ask - best_bid
        bid_depth = sum((p * q for p, q in bids), Decimal(0))
        ask_depth = sum((p * q for p, q in asks), Decimal(0))
        total_top_qty = bid_qty + ask_qty
        imbalance = (bid_qty - ask_qty) / total_top_qty if total_top_qty else Decimal(0)
        return {
            "best_bid": str(best_bid), "best_bid_size": str(bid_qty),
            "best_ask": str(best_ask), "best_ask_size": str(ask_qty),
            "mid_price": str(mid), "spread": str(spread),
            "spread_bps": str((spread / mid) * Decimal(10000)),
            "top_level_imbalance": str(imbalance),
            "bid_notional_depth": str(bid_depth),
            "ask_notional_depth": str(ask_depth),
            "book_valid": True, "depth_levels": self.depth,
            "update_id": self.update_id, "checksum": self.checksum,
        }

    def simulate_market_order(self, side: str, base_quantity: Any) -> dict[str, Any]:
        """Estimate visible-book VWAP and slippage; not an execution guarantee."""
        if not self.valid:
            raise RuntimeError("Order book is invalid; resynchronise before simulation")
        quantity = dec(base_quantity)
        if side not in ("buy", "sell"):
            raise ValueError("side must be buy or sell")
        levels = sorted(self.asks.items()) if side == "buy" else sorted(self.bids.items(), reverse=True)
        remaining = quantity
        filled = Decimal(0)
        notional = Decimal(0)
        for price, available in levels:
            take = min(remaining, available)
            filled += take
            notional += take * price
            remaining -= take
            if remaining == 0:
                break
        if filled == 0:
            raise ValueError("No visible liquidity for requested side")
        vwap = notional / filled
        best = levels[0][0]
        return {
            "side": side, "requested_base_quantity": str(quantity),
            "filled_visible_base_quantity": str(filled),
            "unfilled_base_quantity": str(remaining),
            "filled_notional": str(notional), "visible_book_vwap": str(vwap),
            "best_price": str(best),
            "slippage_bps": str(((vwap - best) / best * Decimal(10000)) if side == "buy"
                                else ((best - vwap) / best * Decimal(10000))),
            "complete": remaining == 0,
            "warning": "Indicative visible-book simulation only; excludes hidden liquidity, latency, fees, queue priority and market movement.",
        }


def _kraken_checksum_component(value: Any) -> str:
    # Kraken specifies string-preserving full precision: strip decimal point
    # and leading zeros, but do not round through binary floating point.
    raw = str(value).replace(".", "")
    return raw.lstrip("0")


def kraken_checksum(bids: dict[Decimal, Decimal], asks: dict[Decimal, Decimal]) -> int:
    ask_levels = sorted(asks.items())[:10]
    bid_levels = sorted(bids.items(), reverse=True)[:10]
    payload = "".join(
        _kraken_checksum_component(price) + _kraken_checksum_component(qty)
        for price, qty in ask_levels + bid_levels
    )
    return zlib.crc32(payload.encode("ascii")) & 0xFFFFFFFF


def apply_kraken_frame(book: OrderBook, frame: dict[str, Any]) -> bool:
    if frame.get("channel") != "book" or not isinstance(frame.get("data"), list) or not frame["data"]:
        raise ValueError("Malformed Kraken book frame")
    item = next((entry for entry in frame["data"]
                 if isinstance(entry, dict) and entry.get("symbol") == book.instrument_id), None)
    if item is None:
        raise ValueError("Kraken book frame does not contain the requested instrument")
    if frame.get("type") == "snapshot":
        book.snapshot(item.get("bids", []), item.get("asks", []),
                      exchange_time=item.get("timestamp"))
        book.checksum = int(item["checksum"])
        if kraken_checksum(book.bids, book.asks) != book.checksum:
            book.valid = False
            return False
        return True
    if frame.get("type") == "update":
        return book.apply_kraken(item.get("bids", []), item.get("asks", []),
                                 int(item["checksum"]), item.get("timestamp"))
    raise ValueError("Unknown Kraken book frame type")
