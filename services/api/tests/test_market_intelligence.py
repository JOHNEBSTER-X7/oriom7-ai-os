from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import commercial_api
import market_intelligence as mi


def snap(ts, bids=None, asks=None):
    return {
        "timestamp": ts,
        "bids": bids or [["99", "2"], ["98", "3"]],
        "asks": asks or [["101", "1"], ["102", "4"]],
    }


def trades():
    return [
        {"timestamp": "2026-11-07T00:00:00Z", "price": "100", "quantity": "2", "aggressor_side": "buy"},
        {"timestamp": "2026-11-07T00:00:01Z", "price": "101", "quantity": "1", "aggressor_side": "sell"},
        {"timestamp": "2026-11-07T00:00:02Z", "price": "100", "quantity": "3", "aggressor_side": "buy"},
    ]


def test_heatmap_normalises_distance_and_notional_depth():
    result = mi.orderbook_heatmap([
        snap("2026-11-07T00:00:00Z"),
        snap("2026-11-07T00:00:01Z", bids=[["100", "1"]], asks=[["102", "2"]]),
    ], top_n=1)
    assert result["snapshot_count"] == 2
    assert result["heatmap"][0]["bids"][0]["notional"] == "198"
    assert result["heatmap"][0]["asks"][0]["distance_bps"] == "100"


def test_heatmap_rejects_crossed_or_one_sided_book():
    with pytest.raises(ValueError, match="uncrossed"):
        mi.orderbook_heatmap([snap("2026-11-07T00:00:00Z", bids=[["102", "1"]], asks=[["101", "1"]])])


def test_wall_analysis_flags_ephemeral_large_liquidity():
    snapshots = [
        snap("2026-11-07T00:00:00Z", bids=[["99", "100"], ["98", "1"]]),
        snap("2026-11-07T00:00:01Z", bids=[["99", "1"], ["98", "1"]]),
        snap("2026-11-07T00:00:02Z", bids=[["99", "1"], ["98", "1"]]),
    ]
    result = mi.liquidity_wall_analysis(snapshots)
    wall = next(x for x in result["walls"] if x["price"] == "99")
    assert wall["size_multiple"] == "100"
    assert wall["research_flag"] == "large_ephemeral_liquidity"
    assert "not proof of spoofing" in result["interpretation"]


def test_flow_pressure_computes_aggressor_notional_imbalance():
    result = mi.flow_pressure(trades())
    assert result["buy_aggressor_notional"] == "500"
    assert result["sell_aggressor_notional"] == "101"
    assert result["signed_notional_delta"] == "399"
    assert result["trade_count"] == 3


def test_volume_profile_groups_trades_and_finds_poc():
    result = mi.volume_profile(trades(), "1")
    assert result["total_quote_volume"] == "601"
    assert result["point_of_control"]["price_from"] == "100"
    assert len(result["levels"]) == 2


def test_regime_classifier_distinguishes_uptrend_and_volatility():
    closes = [str(100 + i * 0.2) for i in range(25)]
    result = mi.regime_classification(closes)
    assert result["regime"].startswith("uptrend_")
    assert result["method"] == "rule_based_20_return_window"


def test_cross_exchange_divergence_and_fragmentation():
    books = [
        {"venue": "venue_a", "bids": [["99", "2"]], "asks": [["101", "2"]]},
        {"venue": "venue_b", "bids": [["100", "2"]], "asks": [["102", "2"]]},
    ]
    result = mi.cross_exchange_analysis(books)
    assert result["venue_count"] == 2
    assert float(result["fragmentation_index"]) > 0
    assert result["venues"][0]["venue"] == "venue_a"


def test_alert_engine_raises_rule_based_signals():
    flow = {"normalised_order_flow_imbalance": "0.8"}
    walls = {"walls": [{"research_flag": "large_ephemeral_liquidity"}]}
    cross = {"fragmentation_index": "15"}
    regime = {"regime": "range_high_volatility"}
    codes = {x["code"] for x in mi.build_alerts(flow, walls, cross, regime)}
    assert codes == {"AGGRESSOR_FLOW_IMBALANCE", "EPHEMERAL_LIQUIDITY_WALL",
                     "CROSS_VENUE_DIVERGENCE", "HIGH_VOLATILITY_REGIME"}


def test_market_intelligence_api_auth_and_metering():
    app = FastAPI()
    app.include_router(mi.router)
    app.dependency_overrides[commercial_api.require_api_key] = lambda: {"owner_id": "acct"}
    usage = []
    async def record(*args, **kwargs):
        usage.append(args)
    mi.record_usage = record
    body = {
        "symbol": "BTCUSDT",
        "venue_books": [
            {"venue": "a", "bids": [["99", "2"]], "asks": [["101", "1"]]},
            {"venue": "b", "bids": [["100", "2"]], "asks": [["102", "1"]]},
        ],
        "snapshots": [
            {"timestamp": "2026-11-07T00:00:00Z", "bids": [["99", "2"]], "asks": [["101", "1"]]},
            {"timestamp": "2026-11-07T00:00:01Z", "bids": [["99", "2"]], "asks": [["101", "1"]]},
        ],
        "trades": trades(),
        "closes": [str(100 + i * 0.1) for i in range(25)],
        "volume_bucket_size": "1"
    }
    response = TestClient(app).post("/v1/market-intelligence/analyse", json=body)
    assert response.status_code == 200
    assert response.json()["object"] == "oriom7_market_intelligence"
    assert response.json()["commentary"]["mode"] == "deterministic_research_summary"
    assert len(usage) == 1


def test_market_intelligence_api_rejects_naive_timestamps():
    with pytest.raises(ValueError, match="timezone"):
        mi._iso(datetime(2026, 11, 7))
