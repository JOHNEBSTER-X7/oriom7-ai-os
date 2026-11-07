from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import commercial_api
import quant_risk
from fastapi import FastAPI
from fastapi.testclient import TestClient


def bars_for(count=100, rate=0.001, phase=0):
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    rows = []
    price = 100.0
    for i in range(count):
        price *= 1 + rate + (((i + phase) % 7) - 3) * 0.0002
        rows.append({
            "timestamp": (start + timedelta(days=i)).isoformat(),
            "open": price * 0.999, "high": price * 1.01,
            "low": price * 0.99, "close": price, "volume": 1000,
        })
    return rows


def payload():
    return {
        "assets": [
            {"symbol": "AAA", "weight": 0.6, "bars": bars_for(rate=0.001, phase=0)},
            {"symbol": "BBB", "weight": 0.4, "bars": bars_for(rate=0.0005, phase=3)},
        ],
        "confidence_level": 0.95,
        "stress_scenarios": [{"name": "risk-off", "shocks": {"AAA": -0.2, "BBB": -0.1}}],
    }


def make_body(**updates):
    value = payload()
    value.update(updates)
    return quant_risk.PortfolioRiskRequest(**value)


def test_portfolio_risk_reports_var_es_drawdown_and_correlation():
    result = quant_risk.run_portfolio_risk(make_body())
    assert result["history"]["return_periods"] == 99
    assert result["historical_tail_risk"]["tail_observations"] >= 1
    assert result["portfolio_performance"]["maximum_drawdown_pct"] >= 0
    assert result["correlation_matrix"]["AAA"]["BBB"] is not None
    assert result["stress_scenarios"][0]["portfolio_return_pct"] < 0
    assert abs(sum(result["risk_contribution_fraction"].values()) - 1) < 1e-5


def test_rejects_weights_that_do_not_sum_to_one():
    value = payload()
    value["assets"][0]["weight"] = 0.5
    try:
        quant_risk.PortfolioRiskRequest(**value)
        assert False, "weights must sum to one"
    except ValueError as exc:
        assert "sum to 1.0" in str(exc)


def test_rejects_misaligned_asset_timestamps():
    value = payload()
    value["assets"][1]["bars"][10]["timestamp"] = (datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(days=10, hours=1)).isoformat()
    try:
        quant_risk.PortfolioRiskRequest(**value)
        assert False, "timestamps must align"
    except ValueError as exc:
        assert "identical aligned timestamps" in str(exc)


def test_endpoint_authenticates_and_meters_usage(monkeypatch):
    app = FastAPI()
    app.include_router(quant_risk.router)
    app.dependency_overrides[commercial_api.require_api_key] = lambda: {
        "api_key_id": "00000000-0000-0000-0000-000000000001",
        "owner_id": "account-a", "plan_code": "starter",
    }
    usage = AsyncMock()
    monkeypatch.setattr(quant_risk, "record_usage", usage)
    response = TestClient(app).post("/v1/quant/risk/portfolio", json=payload())
    assert response.status_code == 200
    assert response.json()["object"] == "oriom7_portfolio_risk"
    usage.assert_awaited_once()
    assert usage.await_args.args[2] == "quant_portfolio_risk"
