from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import commercial_api
import quant_research
from fastapi import FastAPI
from fastapi.testclient import TestClient


def sample_bars(count=40):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    bars = []
    for index in range(count):
        close = 100 + index * 0.5
        bars.append({
            "timestamp": (start + timedelta(days=index)).isoformat(),
            "open": close - 0.2, "high": close + 0.5,
            "low": close - 0.5, "close": close, "volume": 1000 + index,
        })
    return bars


def test_quant_analysis_returns_expected_feature_contract():
    request = quant_research.QuantAnalysisRequest(
        symbol="test", timeframe="1d", bars=sample_bars()
    )
    result = quant_research.analyse_bars(request)
    assert result["symbol"] == "TEST"
    assert result["observations"] == 40
    assert result["indicators"]["ema_12"] > result["indicators"]["ema_26"]
    assert result["indicators"]["annualized_realized_volatility_pct"] >= 0
    assert "no exchange feed is connected" in result["limitations"][0]


def test_quant_analysis_rejects_non_chronological_bars():
    bars = sample_bars()
    bars[2], bars[3] = bars[3], bars[2]
    try:
        quant_research.QuantAnalysisRequest(symbol="X", timeframe="1d", bars=bars)
        assert False, "unordered bars must be rejected"
    except ValueError as exc:
        assert "chronological" in str(exc)


def test_quant_analysis_rejects_invalid_ohlc():
    bars = sample_bars()
    bars[0]["high"] = 1
    try:
        quant_research.QuantAnalysisRequest(symbol="X", timeframe="1d", bars=bars)
        assert False, "invalid OHLC must be rejected"
    except ValueError as exc:
        assert "OHLC" in str(exc)


def test_quant_endpoint_authenticates_and_meters_usage(monkeypatch):
    app = FastAPI()
    app.include_router(quant_research.router)
    app.dependency_overrides[commercial_api.require_api_key] = lambda: {
        "api_key_id": "00000000-0000-0000-0000-000000000001",
        "owner_id": "account-a", "plan_code": "starter",
    }
    usage = AsyncMock()
    monkeypatch.setattr(quant_research, "record_usage", usage)
    response = TestClient(app).post("/v1/quant/analyse", json={
        "symbol": "TEST", "timeframe": "1d", "bars": sample_bars()
    })
    assert response.status_code == 200
    assert response.json()["object"] == "oriom7_quant_analysis"
    usage.assert_awaited_once()
    assert usage.await_args.args[2] == "quant_research"
