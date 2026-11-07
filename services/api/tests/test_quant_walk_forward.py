from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import commercial_api
import quant_walk_forward
from fastapi import FastAPI
from fastapi.testclient import TestClient


def sample_bars(count=260):
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    rows = []
    for i in range(count):
        # Deterministic alternating regimes provide candidate-selection variation.
        trend = (i // 35) % 2
        close = 100 + (i * 0.22 if trend == 0 else 35 - i * 0.12)
        open_price = close - 0.1
        rows.append({
            "timestamp": (start + timedelta(days=i)).isoformat(),
            "open": open_price, "high": close + 0.5,
            "low": open_price - 0.5, "close": close, "volume": 1000,
        })
    return rows


def make_body(**overrides):
    payload = {
        "symbol": "TEST", "timeframe": "1d", "bars": sample_bars(),
        "train_bars": 100, "test_bars": 30, "step_bars": 30,
        "embargo_bars": 5, "fast_candidates": [3, 5],
        "slow_candidates": [10, 15], "fee_bps_per_side": 5,
        "slippage_bps_per_side": 5,
    }
    payload.update(overrides)
    return quant_walk_forward.WalkForwardRequest(**payload)


def test_walk_forward_creates_ordered_disjoint_train_embargo_test_windows():
    result = quant_walk_forward.run_walk_forward(make_body())
    assert result["fold_count"] > 1
    for fold in result["folds"]:
        assert fold["training_observations"] == 100
        assert fold["embargo_observations"] == 5
        assert fold["test_observations"] == 29
        assert fold["train_end_exclusive"] < fold["test_start"]
        assert fold["test_performance"]["scored_periods"] == 30


def test_each_fold_selects_only_from_training_data(monkeypatch):
    original = quant_walk_forward.run_sma_backtest
    seen_lengths = []
    def spy(request):
        seen_lengths.append(len(request.bars))
        return original(request)
    monkeypatch.setattr(quant_walk_forward, "run_sma_backtest", spy)
    result = quant_walk_forward.run_walk_forward(make_body())
    assert seen_lengths
    assert all(length == 100 for length in seen_lengths)
    assert all("training_selection_return_pct" in fold for fold in result["folds"])


def test_test_window_uses_prior_history_but_scores_only_test_periods():
    body = make_body()
    result = quant_walk_forward.run_walk_forward(body)
    first = result["folds"][0]
    assert first["test_performance"]["scored_periods"] == body.test_bars - 1
    assert first["test_start"] == body.bars[body.train_bars + body.embargo_bars].timestamp.isoformat()


def test_rejects_invalid_candidate_grid_and_nonchronological_bars():
    try:
        make_body(fast_candidates=[15], slow_candidates=[10])
        assert False, "invalid candidate grid must fail"
    except ValueError as exc:
        assert "fast candidate" in str(exc)
    values = sample_bars()
    values[10], values[11] = values[11], values[10]
    try:
        make_body(bars=values)
        assert False, "unordered bars must fail"
    except ValueError as exc:
        assert "chronological" in str(exc)


def test_walk_forward_endpoint_authenticates_and_meters_usage(monkeypatch):
    app = FastAPI()
    app.include_router(quant_walk_forward.router)
    app.dependency_overrides[commercial_api.require_api_key] = lambda: {
        "api_key_id": "00000000-0000-0000-0000-000000000001",
        "owner_id": "account-a", "plan_code": "starter",
    }
    usage = AsyncMock()
    monkeypatch.setattr(quant_walk_forward, "record_usage", usage)
    response = TestClient(app).post("/v1/quant/walk-forward", json={
        "symbol": "TEST", "timeframe": "1d", "bars": sample_bars(),
        "train_bars": 100, "test_bars": 30, "step_bars": 30,
        "fast_candidates": [3, 5], "slow_candidates": [10, 15],
    })
    assert response.status_code == 200
    assert response.json()["object"] == "oriom7_quant_walk_forward"
    usage.assert_awaited_once()
    assert usage.await_args.args[2] == "quant_walk_forward"
