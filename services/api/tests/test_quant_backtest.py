from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import commercial_api
import quant_backtest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def bars_with_trend(count=80):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    result = []
    for index in range(count):
        # Rising market followed by a decline to exercise entries and exits.
        close = 100 + index if index < 48 else 148 - (index - 48) * 1.5
        open_price = close - 0.25
        result.append({
            "timestamp": (start + timedelta(days=index)).isoformat(),
            "open": open_price, "high": close + 0.5,
            "low": open_price - 0.5, "close": close, "volume": 10000,
        })
    return result


def make_request(**overrides):
    payload = {
        "symbol": "TEST", "timeframe": "1d", "bars": bars_with_trend(),
        "fast_period": 5, "slow_period": 15,
        "fee_bps_per_side": 5, "slippage_bps_per_side": 5,
    }
    payload.update(overrides)
    return quant_backtest.BacktestRequest(**payload)


def test_backtest_reports_execution_assumptions_and_performance():
    result = quant_backtest.run_sma_backtest(make_request())
    assert result["strategy"] == "long_only_sma_crossover"
    assert result["performance"]["evaluated_periods"] > 0
    assert result["performance"]["completed_position_changes"] >= 2
    assert result["execution_model"]["fill"] == "next bar open"
    assert result["performance"]["maximum_drawdown_pct"] >= 0
    assert result["trades"][0]["reason"] == "prior_close_sma_crossover"
    assert result["limitations"]


def test_backtest_costs_reduce_or_preserve_final_equity():
    free = quant_backtest.run_sma_backtest(make_request(
        fee_bps_per_side=0, slippage_bps_per_side=0
    ))
    costly = quant_backtest.run_sma_backtest(make_request(
        fee_bps_per_side=20, slippage_bps_per_side=20
    ))
    assert costly["performance"]["final_equity"] <= free["performance"]["final_equity"]


def test_backtest_signal_does_not_use_execution_bar_close():
    original = make_request()
    altered_bars = bars_with_trend()
    altered_bars[30]["close"] = 10000
    altered_bars[30]["high"] = 10001
    altered_bars[30]["open"] = 9999
    altered_bars[30]["low"] = 9998
    altered = make_request(bars=altered_bars)
    # The decision/fill at index 30 uses closes strictly before index 30.
    original_result = quant_backtest.run_sma_backtest(original)
    altered_result = quant_backtest.run_sma_backtest(altered)
    first_original = next(t for t in original_result["trades"] if t["timestamp"] == original.bars[30].timestamp.isoformat())
    first_altered = next(t for t in altered_result["trades"] if t["timestamp"] == altered.bars[30].timestamp.isoformat())
    assert first_original["side"] == first_altered["side"]
    assert first_original["fast_sma"] == first_altered["fast_sma"]
    assert first_original["slow_sma"] == first_altered["slow_sma"]


def test_backtest_rejects_invalid_strategy_and_unordered_bars():
    try:
        make_request(fast_period=15, slow_period=15)
        assert False, "fast period must be less than slow period"
    except ValueError as exc:
        assert "fast_period" in str(exc)
    values = bars_with_trend()
    values[5], values[6] = values[6], values[5]
    try:
        make_request(bars=values)
        assert False, "unordered bars must be rejected"
    except ValueError as exc:
        assert "chronological" in str(exc)


def test_backtest_endpoint_authenticates_and_meters_usage(monkeypatch):
    app = FastAPI()
    app.include_router(quant_backtest.router)
    app.dependency_overrides[commercial_api.require_api_key] = lambda: {
        "api_key_id": "00000000-0000-0000-0000-000000000001",
        "owner_id": "account-a", "plan_code": "starter",
    }
    usage = AsyncMock()
    monkeypatch.setattr(quant_backtest, "record_usage", usage)
    response = TestClient(app).post("/v1/quant/backtest", json={
        "symbol": "TEST", "timeframe": "1d", "bars": bars_with_trend(),
        "fast_period": 5, "slow_period": 15,
    })
    assert response.status_code == 200
    assert response.json()["object"] == "oriom7_quant_backtest"
    usage.assert_awaited_once()
    assert usage.await_args.args[2] == "quant_backtest"
