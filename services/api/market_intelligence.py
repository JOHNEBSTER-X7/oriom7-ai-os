"""Deterministic market microstructure and cross-venue intelligence V1.

Research indicators only. A disappearing wall is not proof of spoofing;
it is a cancellation/persistence pattern requiring contextual review.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from statistics import median, pstdev
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from commercial_api import record_usage, require_api_key

router = APIRouter(prefix="/v1/market-intelligence", tags=["market-intelligence"])


def D(value: Any, *, allow_zero: bool = True) -> Decimal:
    try:
        x = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Invalid numeric market-data value") from exc
    if not x.is_finite() or (x < 0 if allow_zero else x <= 0):
        raise ValueError("Market-data value must be finite and non-negative")
    return x


def _iso(value: Any) -> str:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("Timestamps must include a timezone")
    return dt.astimezone(timezone.utc).isoformat()


def _snapshot_levels(snapshot: dict[str, Any]) -> tuple[list[tuple[Decimal, Decimal]], list[tuple[Decimal, Decimal]]]:
    bids = sorted([(D(x[0], allow_zero=False), D(x[1])) for x in snapshot.get("bids", []) if D(x[1]) > 0],
                  reverse=True)
    asks = sorted([(D(x[0], allow_zero=False), D(x[1])) for x in snapshot.get("asks", []) if D(x[1]) > 0])
    if not bids or not asks or bids[0][0] >= asks[0][0]:
        raise ValueError("Each snapshot must contain a valid, uncrossed two-sided book")
    return bids, asks


def orderbook_heatmap(snapshots: list[dict[str, Any]], top_n: int = 20) -> dict[str, Any]:
    if not snapshots or len(snapshots) > 500:
        raise ValueError("Provide between 1 and 500 order-book snapshots")
    rows = []
    for snapshot in snapshots:
        bids, asks = _snapshot_levels(snapshot)
        mid = (bids[0][0] + asks[0][0]) / 2
        rows.append({
            "timestamp": _iso(snapshot["timestamp"]),
            "mid_price": str(mid),
            "bids": [{"price": str(p), "distance_bps": str((mid-p)/mid*10000),
                      "notional": str(p*q), "quantity": str(q)} for p,q in bids[:top_n]],
            "asks": [{"price": str(p), "distance_bps": str((p-mid)/mid*10000),
                      "notional": str(p*q), "quantity": str(q)} for p,q in asks[:top_n]],
        })
    return {"snapshot_count": len(rows), "top_n": top_n, "heatmap": rows,
            "warning": "Snapshots are discrete observations, not a continuous historical depth feed."}


def liquidity_wall_analysis(snapshots: list[dict[str, Any]], multiplier: Decimal = Decimal("3")) -> dict[str, Any]:
    if len(snapshots) < 2 or len(snapshots) > 500:
        raise ValueError("Wall persistence analysis requires 2 to 500 snapshots")
    seen: dict[tuple[str,str], list[Decimal]] = defaultdict(list)
    snapshots_seen = {"bid": [], "ask": []}
    all_sizes = {"bid": [], "ask": []}
    for snap in snapshots:
        bids, asks = _snapshot_levels(snap)
        for side, levels in (("bid", bids), ("ask", asks)):
            current = {str(price): qty for price, qty in levels}
            for price, qty in current.items():
                all_sizes[side].append(qty)
            for key in list(seen):
                if key[0] == side and key[1] not in current:
                    seen[key].append(Decimal(0))
            for price, qty in current.items():
                key = (side, price)
                if key not in seen:
                    seen[key] = [Decimal(0)] * (len(snapshots_seen[side]))
                seen[key].append(qty)
            snapshots_seen[side].append(True)
    walls = []
    for (side, price), sizes in seen.items():
        baseline = median(all_sizes[side]) if all_sizes[side] else Decimal(0)
        peak = max(sizes)
        if baseline <= 0 or peak < baseline * multiplier:
            continue
        qualifying = sum(1 for size in sizes if size >= baseline * multiplier)
        persistence = Decimal(qualifying) / Decimal(len(snapshots))
        disappeared = len(snapshots) - qualifying
        walls.append({
            "side": side, "price": price, "peak_quantity": str(peak),
            "median_side_quantity": str(baseline), "size_multiple": str(peak / baseline),
            "observed_in_snapshots": qualifying, "persistence_ratio": str(persistence),
            "disappearance_ratio": str(Decimal(disappeared) / Decimal(len(snapshots))),
            "research_flag": "large_ephemeral_liquidity" if persistence < Decimal("0.5") else "persistent_large_liquidity",
        })
    walls.sort(key=lambda x: D(x["size_multiple"]), reverse=True)
    return {"wall_count": len(walls), "walls": walls,
            "interpretation": "Disappearance is not proof of spoofing; trade executions, sequence-level event history and venue rules are required."}


def flow_pressure(trades: list[dict[str, Any]]) -> dict[str, Any]:
    if not trades or len(trades) > 100000:
        raise ValueError("Provide between 1 and 100000 trades")
    buy = sell = Decimal(0)
    by_time: dict[str, Decimal] = defaultdict(Decimal)
    ordered = sorted(trades, key=lambda item: _iso(item["timestamp"]))
    prices = []
    for trade in ordered:
        qty, price = D(trade["quantity"], allow_zero=False), D(trade["price"], allow_zero=False)
        side = str(trade["aggressor_side"]).lower()
        if side not in ("buy", "sell"):
            raise ValueError("aggressor_side must be buy or sell")
        ts = _iso(trade["timestamp"])
        notional = qty * price
        if side == "buy":
            buy += notional
            by_time[ts] += notional
        else:
            sell += notional
            by_time[ts] -= notional
        prices.append(price)
    total = buy + sell
    delta = buy - sell
    imbalance = delta / total if total else Decimal(0)
    price_change = prices[-1] - prices[0]
    price_change_bps = price_change / prices[0] * Decimal(10000)
    absorption = abs(imbalance) >= Decimal("0.6") and abs(price_change_bps) <= Decimal("5")
    exhaustion = abs(imbalance) >= Decimal("0.6") and abs(price_change_bps) >= Decimal("50")
    return {
        "buy_aggressor_notional": str(buy), "sell_aggressor_notional": str(sell),
        "signed_notional_delta": str(delta),
        "buy_sell_pressure_ratio": str(buy / sell) if sell else None,
        "normalised_order_flow_imbalance": str(imbalance),
        "trade_count": len(trades), "first_price": str(prices[0]), "last_price": str(prices[-1]),
        "price_change": str(price_change), "price_change_bps": str(price_change_bps),
        "absorption_candidate": absorption, "exhaustion_candidate": exhaustion,
        "interpretation": "Research candidate only; trade direction, price response, book replenishment and time window require contextual validation.",
    }


def volume_profile(trades: list[dict[str, Any]], bucket_size: Any) -> dict[str, Any]:
    step = D(bucket_size, allow_zero=False)
    if not trades or len(trades) > 100000:
        raise ValueError("Provide between 1 and 100000 trades")
    buckets: dict[Decimal, dict[str, Decimal]] = defaultdict(lambda: {"base": Decimal(0), "quote": Decimal(0)})
    for trade in trades:
        price, qty = D(trade["price"], allow_zero=False), D(trade["quantity"], allow_zero=False)
        bucket = (price / step).to_integral_value(rounding="ROUND_FLOOR") * step
        buckets[bucket]["base"] += qty
        buckets[bucket]["quote"] += price * qty
    levels = [{"price_from": str(k), "base_volume": str(v["base"]), "quote_volume": str(v["quote"])}
              for k,v in sorted(buckets.items())]
    poc = max(levels, key=lambda x: D(x["quote_volume"]))
    total = sum((D(x["quote_volume"]) for x in levels), Decimal(0))
    return {"bucket_size": str(step), "levels": levels, "point_of_control": poc,
            "total_quote_volume": str(total)}


def regime_classification(closes: list[Any]) -> dict[str, Any]:
    values = [float(D(x, allow_zero=False)) for x in closes]
    if len(values) < 22 or len(values) > 5000:
        raise ValueError("Regime classification requires 22 to 5000 positive closes")
    returns = [(values[i] / values[i-1]) - 1 for i in range(1, len(values))]
    vol = pstdev(returns[-20:]) if len(returns) >= 20 else pstdev(returns)
    trend = (values[-1] / values[-21]) - 1
    direction = "uptrend" if trend > 0.01 else "downtrend" if trend < -0.01 else "range"
    vol_threshold = 0.01
    volatility = "high_volatility" if vol >= vol_threshold else "low_volatility"
    regime = f"{direction}_{volatility}"
    return {"regime": regime, "directional_return_20": str(trend),
            "realised_volatility_per_bar_20": str(vol),
            "method": "rule_based_20_return_window",
            "warning": "Heuristic regime label, not a predictive model."}


def cross_exchange_analysis(books: list[dict[str, Any]]) -> dict[str, Any]:
    if len(books) < 2 or len(books) > 50:
        raise ValueError("Cross-exchange comparison requires 2 to 50 venue books")
    venues = []
    for item in books:
        bids, asks = _snapshot_levels(item)
        mid = (bids[0][0] + asks[0][0]) / 2
        bid_depth = sum((p*q for p,q in bids), Decimal(0))
        ask_depth = sum((p*q for p,q in asks), Decimal(0))
        venues.append({"venue": str(item["venue"]), "mid_price": mid,
                       "bid_notional_depth": bid_depth, "ask_notional_depth": ask_depth})
    mids = [x["mid_price"] for x in venues]
    reference = sum(mids, Decimal(0)) / len(mids)
    for row in venues:
        row["mid_price"] = str(row["mid_price"])
        row["divergence_bps_vs_mean"] = str((D(row["mid_price"])-reference)/reference*10000)
        row["bid_notional_depth"] = str(row["bid_notional_depth"])
        row["ask_notional_depth"] = str(row["ask_notional_depth"])
    return {"venue_count": len(venues), "reference_mean_mid": str(reference),
            "venues": venues,
            "fragmentation_index": str((max(mids)-min(mids))/reference*10000),
            "warning": "Indicative cross-venue divergence; account for timestamps, fees, transfer constraints and instrument equivalence."}


def build_alerts(flow: dict[str, Any], walls: dict[str, Any], cross: dict[str, Any],
                 regime: dict[str, Any]) -> list[dict[str, str]]:
    alerts = []
    imbalance = D(flow["normalised_order_flow_imbalance"])
    if abs(imbalance) >= Decimal("0.6"):
        alerts.append({"severity": "medium", "code": "AGGRESSOR_FLOW_IMBALANCE",
                       "message": f"Strong { 'buy' if imbalance > 0 else 'sell' } aggressor notional imbalance observed."})
    if any(x["research_flag"] == "large_ephemeral_liquidity" for x in walls["walls"]):
        alerts.append({"severity": "low", "code": "EPHEMERAL_LIQUIDITY_WALL",
                       "message": "A large liquidity level appeared intermittently; investigate cancellations and executions."})
    if D(cross["fragmentation_index"]) >= Decimal("10"):
        alerts.append({"severity": "medium", "code": "CROSS_VENUE_DIVERGENCE",
                       "message": "Cross-venue midpoint divergence exceeds 10 basis points."})
    if "high_volatility" in regime["regime"]:
        alerts.append({"severity": "medium", "code": "HIGH_VOLATILITY_REGIME",
                       "message": "Recent realised volatility exceeds the configured heuristic threshold."})
    return alerts


class SnapshotInput(BaseModel):
    timestamp: datetime
    bids: list[list[str]] = Field(min_length=1, max_length=1000)
    asks: list[list[str]] = Field(min_length=1, max_length=1000)


class TradeInput(BaseModel):
    timestamp: datetime
    price: str
    quantity: str
    aggressor_side: str


class IntelligenceRequest(BaseModel):
    symbol: str = Field(min_length=2, max_length=32)
    venue_books: list[dict[str, Any]] = Field(min_length=2, max_length=50)
    snapshots: list[SnapshotInput] = Field(min_length=2, max_length=500)
    trades: list[TradeInput] = Field(min_length=1, max_length=100000)
    closes: list[str] = Field(min_length=22, max_length=5000)
    volume_bucket_size: str = Field(default="1", min_length=1, max_length=32)
    heatmap_levels: int = Field(default=20, ge=1, le=100)


@router.post("/analyse")
async def analyse_market_intelligence(body: IntelligenceRequest, request: Request,
                                      key: dict = Depends(require_api_key)):
    try:
        snapshots = [x.model_dump(mode="json") for x in body.snapshots]
        trades = [x.model_dump(mode="json") for x in body.trades]
        heatmap = orderbook_heatmap(snapshots, body.heatmap_levels)
        walls = liquidity_wall_analysis(snapshots)
        flow = flow_pressure(trades)
        profile = volume_profile(trades, body.volume_bucket_size)
        regime = regime_classification(body.closes)
        cross = cross_exchange_analysis(body.venue_books)
        alerts = build_alerts(flow, walls, cross, regime)
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result = {
        "object": "oriom7_market_intelligence",
        "version": "v1",
        "symbol": body.symbol.upper(),
        "heatmap": heatmap, "liquidity_walls": walls, "order_flow": flow,
        "volume_profile": profile, "market_regime": regime,
        "cross_exchange": cross, "alerts": alerts,
        "commentary": {
            "mode": "deterministic_research_summary",
            "summary": f"{body.symbol.upper()} is classified as {regime['regime']}; "
                       f"normalised aggressor flow is {flow['normalised_order_flow_imbalance']}; "
                       f"cross-venue midpoint fragmentation is {cross['fragmentation_index']} bps.",
            "llm_context_available": True,
            "warning": "This is rule-generated commentary, not an LLM-generated forecast or investment recommendation."
        },
        "research_only": True,
    }
    observations = len(body.trades) + len(body.closes) + sum(len(x.bids)+len(x.asks) for x in body.snapshots)
    await record_usage(request, key, "market_intelligence_analysis", observations, 200,
                       {"symbol": body.symbol.upper(), "venue_count": len(body.venue_books),
                        "snapshot_count": len(body.snapshots), "trade_count": len(body.trades)})
    return result
